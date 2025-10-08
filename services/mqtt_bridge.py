import os, json

MQTT_DISABLED = os.getenv("MQTT_DISABLED","0") in {"1","true","True"}
MQTT_URL = os.getenv("MQTT_URL","broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT","1883"))
MQTT_PREFIX = os.getenv("MQTT_PREFIX","gaia")

_client = None

def _ensure():
    global _client
    if MQTT_DISABLED:
        return None
    try:
        import paho.mqtt.client as mqtt
        if _client: return _client
        _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        _client.connect(MQTT_URL, MQTT_PORT, keepalive=60)
        _client.loop_start()
        return _client
    except Exception:
        return None

def _pub(topic: str, payload: dict):
    c = _ensure()
    if not c: return
    try:
        c.publish(f"{MQTT_PREFIX}/{topic}", json.dumps(payload), qos=1)
    except Exception:
        pass

def led(room: str, on: bool): _pub(f"{room}/led", {"on": on})
def buzzer(room: str, ms:int=200): _pub(f"{room}/buzzer", {"beep_ms": ms})
def chrono_color(room: str, color: str): _pub(f"{room}/chrono", {"color": color})
