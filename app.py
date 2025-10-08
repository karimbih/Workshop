import os, secrets, time
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, emit
from sqlmodel import SQLModel, Session, create_engine, select
from models import Room, Player
from services import game_state
from services.mqtt_bridge import led, buzzer, chrono_color

# ---------- DB ----------
DB_URI = os.getenv("DB_URI", "sqlite:///mission_gaia.db")
engine = create_engine(DB_URI, echo=False)
SQLModel.metadata.create_all(engine)

# ---------- Flask / Socket.IO ----------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
socketio = SocketIO(
    app,
    async_mode="eventlet",
    cors_allowed_origins="*",
    ping_timeout=30,
    ping_interval=10,
)

MQTT_DISABLED = os.getenv("MQTT_DISABLED", "0") in ("1", "true", "True")

# ---------- Hints / résumé / watchers / score ----------
_HINTS: dict[str, dict[str, int]] = {}
_SUMMARY: dict[str, list] = {}
_WATCHERS: set[str] = set()

# Score & tentatives
POINTS = [2390, 2400, 2431, 2500]
MAX_FAILS_PER_STAGE = 2
_SCORES: dict[str, dict] = {}   # { code: {"by_stage":[int|0], "total":int} }
_FAILS: dict[str, dict] = {}    # { code: {"stage":int, "count":int} }

# Durée par salle
STAGE_DURATIONS = {0: 180, 1: 120, 2: 180, 3: 180}


# --------- Helpers DB ---------
def get_room(code: str) -> Room | None:
    with Session(engine) as s:
        return s.exec(select(Room).where(Room.code == code)).first()


def save(obj):
    with Session(engine) as s:
        s.add(obj)
        s.commit()
        s.refresh(obj)
        return obj


def list_players(code: str):
    with Session(engine) as s:
        return s.exec(select(Player).where(Player.room_code == code)).all()


def get_player(code_room: str, code_player: str) -> Player | None:
    with Session(engine) as s:
        return (
            s.exec(
                select(Player).where(
                    Player.room_code == code_room, Player.code == code_player
                )
            ).first()
        )


# --------- MQTT safe ---------
def safe_led(*args, **kwargs):
    if not MQTT_DISABLED:
        return led(*args, **kwargs)


def safe_buzzer(*args, **kwargs):
    if not MQTT_DISABLED:
        return buzzer(*args, **kwargs)


def safe_chrono_color(*args, **kwargs):
    if not MQTT_DISABLED:
        return chrono_color(*args, **kwargs)


# --------- Timer & state ---------
def ensure_stage_start(r: Room):
    if not r.stage_started_at:
        r.stage_started_at = datetime.now(timezone.utc)
        r.stage_duration_sec = STAGE_DURATIONS.get(r.current_stage, r.stage_duration_sec)
        save(r)


def remaining_stage_time(r: Room) -> int:
    if not r.stage_started_at:
        return r.stage_duration_sec
    elapsed = int((datetime.now(timezone.utc) - r.stage_started_at).total_seconds())
    return max(0, r.stage_duration_sec - elapsed)


def reset_trackers(code: str, stage: int):
    _HINTS[code] = {"stage": stage, "used": 0}
    _SUMMARY[code] = []
    _SCORES[code] = {"by_stage": [], "total": 0}
    _FAILS[code] = {"stage": stage, "count": 0}


def fails_left(code: str, stage: int) -> int:
    fs = _FAILS.get(code) or {"stage": stage, "count": 0}
    if fs["stage"] != stage:
        fs = {"stage": stage, "count": 0}
        _FAILS[code] = fs
    return max(0, MAX_FAILS_PER_STAGE - fs["count"])


def ensure_score_len(code: str, stage: int):
    # Remplit _SCORES[code]["by_stage"] jusqu'à 'stage'-1 en mettant 0 si manquant
    sc = _SCORES.setdefault(code, {"by_stage": [], "total": 0})
    while len(sc["by_stage"]) < stage:
        sc["by_stage"].append(0)


def add_points(code: str, stage: int, pts: int):
    sc = _SCORES.setdefault(code, {"by_stage": [], "total": 0})
    ensure_score_len(code, stage)
    if len(sc["by_stage"]) == stage:  # on ajoute pour ce stage
        sc["by_stage"].append(pts)
        sc["total"] += pts


def state_payload(r: Room):
    prompt = None
    if not r.is_finished:
        prompt = game_state.get_stage_prompt(r.current_stage)
    sc = _SCORES.get(r.code) or {"by_stage": [], "total": 0}
    return {
        "stage": r.current_stage,
        "total": game_state.total_stages(),
        "prompt": prompt,
        "remaining": remaining_stage_time(r),
        "finished": r.is_finished,
        "success": r.success,
        "hints": (_HINTS.get(r.code) or {"stage": r.current_stage, "used": 0})
        | {"total": len(getattr(game_state, "PUZZLES", []))},
        "room_label": r.code,
        "score": {"total": sc["total"], "by_stage": sc["by_stage"], "fails_left": fails_left(r.code, r.current_stage)},
    }


# --------- Watcher (chrono + auto passage) ---------
def start_watcher(code: str):
    if code in _WATCHERS:
        return
    _WATCHERS.add(code)

    def _run():
        last_color = None
        while True:
            r = get_room(code)
            if not r:
                break
            rem = remaining_stage_time(r)
            dur = r.stage_duration_sec
            ratio = rem / max(1, dur)
            color = "green" if ratio >= 0.6 else ("yellow" if ratio >= 0.3 else "red")
            if r.is_finished:
                color = "off"
            if color != last_color:
                safe_chrono_color(code, color)
                last_color = color

            if not r.is_finished and rem <= 0:
                # Temps écoulé => 0 point pour cette salle
                add_points(code, r.current_stage, 0)
                r.missed_count += 1
                r.current_stage += 1
                if r.current_stage >= game_state.total_stages():
                    r.is_finished = True
                    r.success = (_SCORES.get(code, {"total": 0})["total"] > 0)
                else:
                    r.stage_started_at = datetime.now(timezone.utc)
                    r.stage_duration_sec = STAGE_DURATIONS.get(
                        r.current_stage, r.stage_duration_sec
                    )
                    _HINTS[code] = {"stage": r.current_stage, "used": 0}
                    _FAILS[code] = {"stage": r.current_stage, "count": 0}
                save(r)
                socketio.emit(
                    "chat",
                    {
                        "system": True,
                        "msg": "⏰ Temps écoulé pour cette énigme. Passage à la suivante.",
                    },
                    room=code,
                )
                socketio.emit("state", state_payload(r), room=code)
                if r.is_finished:
                    socketio.emit(
                        "summary", {"items": _SUMMARY.get(code, []), "score": _SCORES.get(code)}, room=code
                    )
                    break
            if r.is_finished:
                break
            time.sleep(1.5)
        safe_chrono_color(code, "off")
        _WATCHERS.discard(code)

    socketio.start_background_task(_run)


# --------- Routes ---------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        code = request.form.get("room_code") or secrets.token_hex(1).upper()
        r = get_room(code)
        if not r:
            r = save(Room(code=code))
            with Session(engine) as s:
                for c in (generate_player_codes := [secrets.token_hex(3).upper() for _ in range(4)]):
                    s.add(Player(room_code=code, code=c))
                s.commit()
        if r.code not in _SCORES:
            reset_trackers(r.code, r.current_stage)
        return redirect(url_for("room", code=code))
    return render_template("index.html")


@app.route("/room/<code>")
def room(code):
    r = get_room(code)
    if not r:
        return redirect(url_for("index"))

    if request.args.get("reset") == "1":
        r.started_at = None
        r.stage_started_at = None
        r.current_stage = 0
        r.is_finished = False
        r.success = False
        r.missed_count = 0
        r.stage_duration_sec = STAGE_DURATIONS.get(0, r.stage_duration_sec)
        save(r)
        reset_trackers(code, r.current_stage)
        with Session(engine) as s:
            ps = s.exec(select(Player).where(Player.room_code == code)).all()
            for p in ps:
                p.authenticated = False
                p.name = None
                s.add(p)
            s.commit()

    if code not in _HINTS:
        reset_trackers(code, r.current_stage)
    players = list_players(code)
    return render_template("room.html", room_code=code, players=players)


# --------- Socket.IO events ---------
@socketio.on("auth")
def on_auth(data):
    room_code = data.get("room")
    pcode = (data.get("player_code") or "").strip().upper()
    name = (data.get("name") or "").strip() or "Agent"
    p = get_player(room_code, pcode)
    if not p:
        emit("auth_result", {"ok": False, "msg": "Code joueur invalide."})
        return
    p.name = name
    p.authenticated = True
    save(p)
    join_room(room_code)
    emit("auth_result", {"ok": True, "msg": f"Bienvenue {name} !"})
    emit("chat", {"system": True, "msg": f"{name} est connecté."}, room=room_code)
    r = get_room(room_code)
    if r:
        emit("state", state_payload(r))


@socketio.on("start")
def on_start(data):
    code = data.get("room")
    r = get_room(code)
    if not r:
        return

    if r.is_finished:
        r.started_at = datetime.now(timezone.utc)
        r.stage_started_at = datetime.now(timezone.utc)
        r.current_stage = 0
        r.is_finished = False
        r.success = False
        r.missed_count = 0
        r.stage_duration_sec = STAGE_DURATIONS.get(0, r.stage_duration_sec)
        save(r)
        reset_trackers(code, r.current_stage)
        start_watcher(code)
        emit("chat", {"system": True, "msg": "🔁 Nouvelle partie !"}, room=code)
        emit("state", state_payload(r), room=code)
        return

    if not r.started_at:
        r.started_at = datetime.now(timezone.utc)
        r.stage_started_at = datetime.now(timezone.utc)
        r.stage_duration_sec = STAGE_DURATIONS.get(0, r.stage_duration_sec)
        save(r)
        reset_trackers(code, r.current_stage)
        start_watcher(code)
        emit("chat", {"system": True, "msg": "La mission démarre !"}, room=code)
        emit("state", state_payload(r), room=code)


@socketio.on("hint")
def on_hint(data):
    code = data.get("room")
    r = get_room(code)
    if not r or r.is_finished:
        return
    hs = _HINTS.get(code) or {"stage": r.current_stage, "used": 0}
    if hs["stage"] != r.current_stage:
        hs = {"stage": r.current_stage, "used": 0}
        _HINTS[code] = hs
    nxt = game_state.get_hint(r.current_stage, hs["used"])
    if nxt:
        hs["used"] += 1
        emit("chat", {"system": True, "msg": f"🧩 Indice {hs['used']}: {nxt}"}, room=code)
    else:
        emit("chat", {"system": True, "msg": "Aucun indice supplémentaire disponible."}, room=code)
    emit("state", state_payload(r), room=code)


@socketio.on("chat_message")
def on_chat_message(data):
    code = data.get("room")
    text = (data.get("text") or "").strip()
    name = (data.get("name") or "Agent").strip()
    if not code or not text:
        return
    emit("chat", {"system": False, "msg": f"{name}: {text}"}, room=code)


@socketio.on("submit")
def on_submit(data):
    code = data.get("room")
    payload = data.get("payload", {})
    r = get_room(code)
    if not r or r.is_finished:
        return
    if remaining_stage_time(r) <= 0:
        return

    cur = r.current_stage
    ok = game_state.validate_stage(cur, payload)

    # Maintenir compteur de fails par salle
    fs = _FAILS.get(code) or {"stage": cur, "count": 0}
    if fs["stage"] != cur:
        fs = {"stage": cur, "count": 0}
    _FAILS[code] = fs

    if ok:
        safe_led(code, True)
        safe_buzzer(code, 120)
        # Points gagnés
        add_points(code, cur, POINTS[cur])

        debrief = game_state.get_debrief(cur)
        if debrief:
            prompt = game_state.get_stage_prompt(cur)
            _SUMMARY.setdefault(code, []).append(
                {"stage": cur, "title": prompt.get("title", ""), "debrief": debrief}
            )
            emit("chat", {"system": True, "msg": "🎓 Débrief: " + debrief}, room=code)

        # Étape suivante
        r.current_stage += 1
        if r.current_stage >= game_state.total_stages():
            r.is_finished = True
            r.success = (_SCORES.get(code, {"total": 0})["total"] > 0)
        else:
            r.stage_started_at = datetime.now(timezone.utc)
            r.stage_duration_sec = STAGE_DURATIONS.get(
                r.current_stage, r.stage_duration_sec
            )
            _HINTS[code] = {"stage": r.current_stage, "used": 0}
            _FAILS[code] = {"stage": r.current_stage, "count": 0}
        save(r)
        emit("chat", {"system": True, "msg": "✅ Énigme réussie ! (+%d pts)" % POINTS[cur]}, room=code)

    else:
        fs["count"] += 1
        if cur == 1 and r.stage_started_at:
            # Salle Abeille -> -30s à chaque erreur
            r.stage_started_at = r.stage_started_at - timedelta(seconds=30)
            save(r)
            emit("chat", {"system": True, "msg": "❌ Mauvaise réponse (−30s)."}, room=code)
        else:
            emit("chat", {"system": True, "msg": "❌ Mauvaise réponse."}, room=code)

        # Si > 2 tentatives => 0 point et on passe
        if fs["count"] >= MAX_FAILS_PER_STAGE:
            add_points(code, cur, 0)
            r.current_stage += 1
            if r.current_stage >= game_state.total_stages():
                r.is_finished = True
                r.success = (_SCORES.get(code, {"total": 0})["total"] > 0)
            else:
                r.stage_started_at = datetime.now(timezone.utc)
                r.stage_duration_sec = STAGE_DURATIONS.get(
                    r.current_stage, r.stage_duration_sec
                )
                _HINTS[code] = {"stage": r.current_stage, "used": 0}
                _FAILS[code] = {"stage": r.current_stage, "count": 0}
            save(r)
            emit("chat", {"system": True, "msg": "⚠️ Plus de tentatives. 0 point et prochaine énigme."}, room=code)

        safe_buzzer(code, 300)

    emit("state", state_payload(r), room=code)
    if r.is_finished:
        socketio.emit(
            "summary", {"items": _SUMMARY.get(code, []), "score": _SCORES.get(code)}, room=code
        )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5050)))

