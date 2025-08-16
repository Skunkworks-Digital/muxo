from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.devices.serial_port import probe_modems
from backend.sms.sender import send_sms

app = FastAPI()


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
def api_send(message: Message) -> dict[str, str]:
    try:
        ref = send_sms(message.msisdn, message.text, message.device_id)
    except Exception as exc:  # pragma: no cover - surface error
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ref": ref}
