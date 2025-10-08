import os, secrets, time
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, emit
from sqlmodel import SQLModel, Session, create_engine, select
from models import Room, Player
from services import game_state
from services.mqtt_bridge import led, buzzer, chrono_color

DB_URI = os.getenv("DB_URI", "sqlite:///mission_gaia.db")
engine = create_engine(DB_URI, echo=False)
SQLModel.metadata.create_all(engine)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# Durées par salle (sec)
STAGE_DURATIONS = {0: 120, 1: 120, 2: 180, 3: 180}

# Indices (facultatif)
_HINTS: dict[str, dict[str, int]] = {}
_WATCHERS: set[str] = set()

def utcnow():
    return datetime.now(timezone.utc)

def as_aware(dt):
    if dt is None: return None
    if dt.tzinfo is None: return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def get_room(code: str) -> Room|None:
    with Session(engine) as s:
        return s.exec(select(Room).where(Room.code==code)).first()

def save(obj):
    with Session(engine) as s:
        s.add(obj); s.commit(); s.refresh(obj); return obj

def list_players(code: str):
    with Session(engine) as s:
        return s.exec(select(Player).where(Player.room_code==code)).all()

def get_player(code_room: str, code_player: str) -> Player|None:
    with Session(engine) as s:
        return s.exec(select(Player).where(Player.room_code==code_room, Player.code==code_player)).first()

def ensure_stage_start(r: Room):
    if not r.stage_started_at:
        r.stage_started_at = utcnow()
        save(r)

def remaining_stage_time(r: Room) -> int:
    start = as_aware(r.stage_started_at)
    if not start:
        return r.stage_duration_sec
    elapsed = int((utcnow() - start).total_seconds())
    return max(0, r.stage_duration_sec - elapsed)

def hints_info(code: str, stage: int) -> dict:
    hs = _HINTS.get(code) or {"stage": stage, "used": 0}
    if hs["stage"] != stage:
        hs = {"stage": stage, "used": 0}; _HINTS[code] = hs
    return {"used": hs["used"], "total": 0}  # pas d'indices textuels ici

def state_payload(r: Room):
    prompt = None
    if not r.is_finished:
        prompt = game_state.get_stage_prompt(r.current_stage)
    return {
        "stage": r.current_stage,
        "total": game_state.total_stages(),
        "prompt": prompt,
        "remaining": remaining_stage_time(r),
        "finished": r.is_finished,
        "success": r.success,
        "score": r.score,
        "hints": hints_info(r.code, r.current_stage)
    }

def generate_player_codes(n=4):
    return [secrets.token_hex(3).upper() for _ in range(n)]

def start_watcher(code: str):
    if code in _WATCHERS: return
    _WATCHERS.add(code)
    def _run():
        last_color = None
        while True:
            r = get_room(code)
            if not r: break
            rem = remaining_stage_time(r)
            dur = r.stage_duration_sec
            ratio = rem / max(1, dur)
            color = "green" if ratio >= 0.6 else ("yellow" if ratio >= 0.3 else "red")
            if r.is_finished: color = "off"
            if color != last_color:
                chrono_color(code, color); last_color = color

            if not r.is_finished and rem <= 0:
                r.missed_count += 1
                r.wrong_attempts = 0
                r.current_stage += 1
                if r.current_stage >= game_state.total_stages():
                    r.is_finished = True
                    r.success = (r.missed_count == 0)
                else:
                    r.stage_started_at = utcnow()
                    r.stage_duration_sec = STAGE_DURATIONS.get(r.current_stage, r.stage_duration_sec)
                save(r)
                socketio.emit("chat", {"system":True, "msg":"⏰ Temps écoulé. Passage à la salle suivante."}, room=code)
                socketio.emit("state", state_payload(r), room=code)
                if r.is_finished: break
            if r.is_finished: break
            time.sleep(1.0)
        chrono_color(code, "off")
        _WATCHERS.discard(code)
    socketio.start_background_task(_run)

@app.route("/", methods=["GET","POST"])
def index():
    if request.method=="POST":
        code = request.form.get("room_code") or secrets.token_hex(2).upper()
        r = get_room(code)
        if not r:
            r = save(Room(code=code, stage_duration_sec=STAGE_DURATIONS.get(0,120)))
            with Session(engine) as s:
                for c in generate_player_codes(4):
                    s.add(Player(room_code=code, code=c))
                s.commit()
        return redirect(url_for("room", code=code))
    return render_template("index.html")

@app.route("/room/<code>")
def room(code):
    r = get_room(code)
    if not r: return redirect(url_for("index"))
    players = list_players(code)
    return render_template("room.html", room_code=code, players=players)

@socketio.on("auth")
def on_auth(data):
    room_code = data.get("room")
    pcode = (data.get("player_code") or "").strip().upper()
    name = (data.get("name") or "").strip() or "Agent"
    p = get_player(room_code, pcode)
    if not p:
        emit("auth_result", {"ok": False, "msg": "Code joueur invalide."})
        return
    p.name = name; p.authenticated = True; save(p)
    join_room(room_code)
    emit("auth_result", {"ok": True, "msg": f"Bienvenue {name} !"})
    emit("chat", {"system":True, "msg": f"{name} est connecté."}, room=room_code)
    r = get_room(room_code)
    if r: emit("state", state_payload(r))

@socketio.on("start")
def on_start(data):
    code = data.get("room"); r = get_room(code)
    if not r: return
    # Autoriser le start si partie finie (rejouer via start)
    if r.started_at and not r.is_finished:
        return
    # démarrage / redémarrage
    r.is_finished = False; r.success=False
    r.current_stage = 0
    r.missed_count = 0
    r.wrong_attempts = 0
    r.score = 0
    r.started_at = utcnow()
    r.stage_started_at = utcnow()
    r.stage_duration_sec = STAGE_DURATIONS.get(0, 120)
    save(r)
    start_watcher(code)
    emit("chat", {"system":True,"msg":"La mission démarre !"}, room=code)
    emit("state", state_payload(r), room=code)

@socketio.on("replay")
def on_replay(data):
    code = data.get("room"); r = get_room(code)
    if not r: return
    r.is_finished = False; r.success=False
    r.current_stage = 0
    r.missed_count = 0
    r.wrong_attempts = 0
    r.score = 0
    r.started_at = utcnow()
    r.stage_started_at = utcnow()
    r.stage_duration_sec = STAGE_DURATIONS.get(0, 120)
    save(r)
    start_watcher(code)
    emit("chat", {"system":True,"msg":"🔁 Rejouer : partie relancée."}, room=code)
    emit("state", state_payload(r), room=code)

@socketio.on("hint")
def on_hint(data):
    code = data.get("room"); r = get_room(code)
    if not r or r.is_finished: return
    emit("chat", {"system":True, "msg": "Indices non disponibles sur cette version."}, room=code)
    emit("state", state_payload(r), room=code)

@socketio.on("chat_message")
def on_chat_message(data):
    code = data.get("room"); text = (data.get("text") or "").strip()
    name = (data.get("name") or "Agent").strip()
    if not code or not text: return
    emit("chat", {"system":False, "msg": f"{name}: {text}"}, room=code)

def advance_to_next_stage(r: Room, award_score: int):
    if award_score > 0:
        r.score += award_score
    r.current_stage += 1
    r.wrong_attempts = 0
    if r.current_stage >= game_state.total_stages():
        r.is_finished=True
        r.success = True
    else:
        r.stage_started_at = utcnow()
        r.stage_duration_sec = STAGE_DURATIONS.get(r.current_stage, r.stage_duration_sec)
    save(r)

@socketio.on("submit")
def on_submit(data):
    code = data.get("room"); payload = data.get("payload",{})
    r = get_room(code)
    if not r or r.is_finished: return
    if remaining_stage_time(r) <= 0:
        return
    cur = r.current_stage
    ok = game_state.validate_stage(cur, payload)
    if ok:
        led(code, True); buzzer(code, 120)
        emit("chat", {"system":True,"msg":"✅ Bonne réponse !"}, room=code)
        # score
        award = game_state.stage_score(cur)
        advance_to_next_stage(r, award)
        emit("state", state_payload(r), room=code)
    else:
        r.wrong_attempts += 1
        save(r)
        buzzer(code, 300)
        # règle spéciale salle 2 : -30s
        if cur == 1 and r.stage_started_at:
            r.stage_started_at = as_aware(r.stage_started_at) - timedelta(seconds=30)
            save(r)
            emit("chat", {"system":True,"msg":"❌ Mauvaise réponse — la biodiversité s’effondre… (-30s)"}, room=code)
        else:
            emit("chat", {"system":True,"msg":"❌ Mauvaise réponse."}, room=code)
        # si >2 erreurs, 0 point et on avance
        if r.wrong_attempts >= 2:
            emit("chat", {"system":True,"msg":"😕 Trop d'erreurs sur cette salle — 0 point. On avance."}, room=code)
            advance_to_next_stage(r, 0)
        emit("state", state_payload(r), room=code)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5050)))
