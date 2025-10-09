import os, secrets, time
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, emit
from sqlmodel import SQLModel, Session, create_engine, select
from models import Room, Player
from services import game_state
from services.mqtt_bridge import led, buzzer, chrono_color

# ------------------ DB / APP / SOCKET ------------------
DB_URI = os.getenv("DB_URI", "sqlite:///mission_gaia.db")
engine = create_engine(DB_URI, echo=False)
SQLModel.metadata.create_all(engine)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# ------------------ MEMOIRES EN RAM ------------------
_HINTS: dict[str, dict[str, int]] = {}
_SUMMARY: dict[str, list] = {}
_WATCHERS: set[str] = set()

# --- NEW : Codes par salle & stockage par room
_STAGE_CODES = {     # index d'étape -> code
    0: 2390,         # Salle 1 (Tri)
    1: 2400,         # Salle 2 (Abeille)
    2: 2431,         # Salle 3 (Energie 180 MW)
}
_CODES: dict[str, dict[int, int]] = {}  # room_code -> {stage_index: code}

# ------------------ HELPERS ------------------
def get_room(code: str) -> Room | None:
    with Session(engine) as s:
        return s.exec(select(Room).where(Room.code == code)).first()

def save(obj):
    with Session(engine) as s:
        s.add(obj); s.commit(); s.refresh(obj); return obj

def list_players(code: str):
    with Session(engine) as s:
        return s.exec(select(Player).where(Player.room_code == code)).all()

def get_player(code_room: str, code_player: str) -> Player | None:
    with Session(engine) as s:
        return s.exec(select(Player).where(
            Player.room_code == code_room,
            Player.code == code_player
        )).first()

def remaining_stage_time(r: Room) -> int:
    """Temps restant en secondes pour l'étape courante."""
    if not r.stage_started_at:
        return r.stage_duration_sec
    # On normalise en timezone-aware UTC si besoin
    started = r.stage_started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = int((datetime.now(timezone.utc) - started).total_seconds())
    return max(0, r.stage_duration_sec - elapsed)

def hints_info(code: str, stage: int) -> dict:
    hs = _HINTS.get(code) or {"stage": stage, "used": 0}
    if hs["stage"] != stage:
        hs = {"stage": stage, "used": 0}; _HINTS[code] = hs
    p = game_state.PUZZLES[stage] if stage < game_state.total_stages() else None
    total = len(getattr(p, "hints", [])) if p else 0
    return {"used": hs["used"], "total": total}

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
        "hints": hints_info(r.code, r.current_stage)
    }

def reset_trackers(code: str, stage: int):
    _HINTS[code] = {"stage": stage, "used": 0}
    _SUMMARY[code] = []
    _CODES[code] = {}               # --- NEW : reset des codes pour cette room

def generate_player_codes(n=4):
    return [secrets.token_hex(3).upper() for _ in range(n)]  # 6 chars

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
                r.current_stage += 1
                if r.current_stage >= game_state.total_stages():
                    r.is_finished = True
                    r.success = (r.missed_count == 0)
                else:
                    r.stage_started_at = datetime.now(timezone.utc)
                    _HINTS[code] = {"stage": r.current_stage, "used": 0}
                save(r)
                socketio.emit("chat", {"system":True, "msg":"⏰ Temps écoulé pour cette énigme. Passage à la suivante."}, room=code)
                socketio.emit("state", state_payload(r), room=code)
                if r.is_finished:
                    socketio.emit("summary", {"items": _SUMMARY.get(code, [])}, room=code)
                    break
            if r.is_finished: break
            time.sleep(1.2)
        chrono_color(code, "off")
        _WATCHERS.discard(code)
    socketio.start_background_task(_run)

# ------------------ ROUTES ------------------
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        code_form = (request.form.get("room_code") or "").strip()
        team_name = (request.form.get("team_name") or "").strip()
        code = code_form or secrets.token_hex(2).upper()

        r = get_room(code)
        if not r:
            r = save(Room(code=code, team_name=team_name or f"Équipe {code}"))
            with Session(engine) as s:
                for c in generate_player_codes(4):
                    s.add(Player(room_code=code, code=c))
                s.commit()
        reset_trackers(code, r.current_stage)
        return redirect(url_for("room", code=code))
    return render_template("index.html")

@app.route("/room/<code>")
def room(code):
    r = get_room(code)
    if not r: return redirect(url_for("index"))
    if code not in _HINTS: reset_trackers(code, r.current_stage)
    players = list_players(code)
    return render_template("room.html", room_code=code, players=players)

# ------------------ SOCKETS ------------------
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
    # Autoriser démarrage même si partie finie (pour Rejouer), ou vérifier min 2 joueurs si partie neuve
    if r.started_at and not r.is_finished:
        emit("chat", {"system":True, "msg":"La mission est déjà en cours."}, room=code)
        return
    # Démarrage/Redémarrage
    r.started_at = datetime.now(timezone.utc)
    r.stage_started_at = datetime.now(timezone.utc)
    r.is_finished = False
    r.success = False
    r.current_stage = 0 if r.missed_count > 0 or r.started_at else r.current_stage
    save(r)
    start_watcher(code)
    emit("chat", {"system":True,"msg":"La mission démarre !"}, room=code)
    emit("state", state_payload(r), room=code)

@socketio.on("replay")
def on_replay(data):
    code = data.get("room"); r = get_room(code)
    if not r: return
    # Remise à zéro contrôlée (sans toucher à la DB structurelle)
    r.is_finished = False
    r.success = False
    r.missed_count = 0
    r.current_stage = 0
    r.stage_started_at = datetime.now(timezone.utc)
    save(r)
    reset_trackers(code, 0)
    start_watcher(code)
    emit("chat", {"system":True,"msg":"🔁 Rejouer : la salle a été réinitialisée."}, room=code)
    emit("state", state_payload(r), room=code)

@socketio.on("hint")
def on_hint(data):
    code = data.get("room"); r = get_room(code)
    if not r or r.is_finished: return
    hs = _HINTS.get(code) or {"stage": r.current_stage, "used": 0}
    if hs["stage"] != r.current_stage:
        hs = {"stage": r.current_stage, "used": 0}; _HINTS[code]=hs
    nxt = game_state.get_hint(r.current_stage, hs["used"])
    if nxt:
        hs["used"] += 1
        emit("chat", {"system":True, "msg": f"🧩 Indice {hs['used']}: {nxt}"}, room=code)
    else:
        emit("chat", {"system":True, "msg": "Aucun indice supplémentaire disponible."}, room=code)
    emit("state", state_payload(r), room=code)

@socketio.on("chat_message")
def on_chat_message(data):
    code = data.get("room"); text = (data.get("text") or "").strip()
    name = (data.get("name") or "Agent").strip()
    if not code or not text: return
    emit("chat", {"system":False, "msg": f"{name}: {text}"}, room=code)

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
        # --- Feedback matériel
        led(code, True); buzzer(code, 120)

        # --- Débrief éventuel
        debrief = game_state.get_debrief(cur)
        if debrief:
            prompt = game_state.get_stage_prompt(cur)
            _SUMMARY.setdefault(code, []).append({
                "stage": cur,
                "title": prompt.get("title",""),
                "debrief": debrief
            })
            emit("chat", {"system":True,"msg":"🎓 Débrief: " + debrief}, room=code)

        # --- NEW : code de l'étape
        if cur in _STAGE_CODES:
            val = _STAGE_CODES[cur]
            _CODES.setdefault(code, {})[cur] = val
            emit("chat", {"system": True, "msg": f"🔐 Code {cur+1} = {val}"}, room=code)

        # Passage à l'étape suivante
        r.current_stage += 1
        if r.current_stage >= game_state.total_stages():
            r.is_finished=True
            r.success = (r.missed_count == 0)
        else:
            r.stage_started_at = datetime.now(timezone.utc)
        save(r)

        # --- NEW : à l’entrée en salle 4, donner l’indice final
        if not r.is_finished and r.current_stage == 3:
            cs = _CODES.get(code, {})
            if all(k in cs for k in (0, 1, 2)):
                total = cs[0] + cs[1] + cs[2]
                moyenne = round(total / 3)
                emit(
                    "chat",
                    {"system": True,
                     "msg": f"🧩 Indice final : faites la moyenne des 3 codes. "
                            f"(Code1 + Code2 + Code3) / 3 = {moyenne}. "
                            f"Interprétez-le comme JJMM pour trouver la date."},
                    room=code
                )

        _HINTS[code] = {"stage": r.current_stage, "used": 0}
        emit("chat", {"system":True,"msg":"✅ Énigme réussie !"}, room=code)

    else:
        buzzer(code, 300)
        emit("chat", {"system":True,"msg":"❌ Mauvaise réponse."}, room=code)

    emit("state", state_payload(r), room=code)
    if r.is_finished:
        socketio.emit("summary", {"items": _SUMMARY.get(code, [])}, room=code)

# ------------------ MAIN ------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5050)))

