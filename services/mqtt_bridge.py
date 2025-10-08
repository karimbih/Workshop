import os, json, ssl

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

MQTT_URL    = os.getenv("MQTT_URL", "broker.hivemq.com")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TLS    = os.getenv("MQTT_TLS", "false").lower() == "true"
MQTT_PREFIX = os.getenv("MQTT_PREFIX", "gaia")
DISABLED    = os.getenv("MQTT_DISABLED", "0").lower() in ("1","true","yes")

_client = None
_failed = False

def _ensure():
    global _client, _failed
    if DISABLED or mqtt is None:
        return None
    if _failed:
        return None
    if _client:
        return _client
    try:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if MQTT_TLS:
            c.tls_set(cert_reqs=ssl.CERT_REQUIRED)
            port = 8883
        else:
            port = MQTT_PORT
        c.connect(MQTT_URL, port, keepalive=60)
        c.loop_start()
        _client = c
        return _client
    except Exception as e:
        _failed = True
        print(f"[MQTT] désactivé: {e}")
        return None

def _pub(topic: str, payload: dict):
    c = _ensure()
    if not c:
        return
    try:
        c.publish(topic, json.dumps(payload), qos=1)
    except Exception as e:
        print(f"[MQTT] publish erreur: {e}")

def led(room: str, on: bool):
    _pub(f"{MQTT_PREFIX}/{room}/led", {"on": bool(on)})

def buzzer(room: str, ms: int = 300):
    _pub(f"{MQTT_PREFIX}/{room}/buzzer", {"beep_ms": int(ms)})

def chrono_color(room: str, color: str):
    if color not in {"green", "yellow", "red", "off"}:
        color = "off"
    _pub(f"{MQTT_PREFIX}/{room}/chrono", {"color": color})

