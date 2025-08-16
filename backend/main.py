from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.devices.serial_port import probe_modems
from backend.sms.receiver import start_receiver
from backend.sms.sender import send_sms
from backend.sms.store import INBOX

app = FastAPI()
RECEIVERS: list = []


@app.on_event("startup")
def _startup() -> None:
    for dev in probe_modems():
        if dev.get("sim_ready"):
            RECEIVERS.append(start_receiver(dev["port"]))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/devices/probe")
def api_probe() -> list[dict]:
    return probe_modems()


class Message(BaseModel):
    msisdn: str
    text: str
    device_id: str


@app.post("/api/messages")
def api_send(message: Message) -> dict[str, list[str]]:
    try:
        refs = send_sms(message.msisdn, message.text, message.device_id)
    except Exception as exc:  # pragma: no cover - surface error
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"refs": refs}


@app.get("/api/inbox")
def api_inbox() -> list[dict]:
    return INBOX
