"""FastAPI application with campaign scheduling and CRUD APIs."""

from __future__ import annotations

import itertools
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import SessionLocal, get_session
from backend.devices.serial_port import probe_modems
from backend.models import (
    Campaign,
    Contact,
    Device,
    ListMember,
    Message,
)
from backend.sms.receiver import start_receiver
from backend.sms.sender import send_sms
from backend.sms.store import INBOX


app = FastAPI()
RECEIVERS: list = []
SCHEDULER = BackgroundScheduler()


@app.on_event("startup")
def _startup() -> None:
    SCHEDULER.start()
    for dev in probe_modems():
        if dev.get("sim_ready"):
            RECEIVERS.append(start_receiver(dev["port"]))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/devices/probe")
def api_probe() -> list[dict]:
    return probe_modems()


class MessageIn(BaseModel):
    msisdn: str
    text: str
    device_id: str


@app.post("/api/messages")
def api_send(message: MessageIn, db: Session = Depends(get_session)) -> dict[str, object]:
    device = db.query(Device).filter(Device.port == message.device_id).first()
    if not device:
        raise HTTPException(status_code=400, detail="device not found")
    contact = db.query(Contact).filter(Contact.msisdn == message.msisdn).first()
    if not contact:
        contact = Contact(msisdn=message.msisdn)
        db.add(contact)
        db.commit()
        db.refresh(contact)
    try:
        refs = send_sms(message.msisdn, message.text, message.device_id)
    except Exception as exc:  # pragma: no cover - surface error
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    msg = Message(
        contact_id=contact.id,
        device_id=device.id,
        text=message.text,
        ref=refs[0] if refs else None,
        status="sent",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "refs": refs}


@app.get("/api/messages/{message_id}")
def api_message(message_id: int, db: Session = Depends(get_session)) -> dict:
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": msg.id,
        "status": msg.status,
        "error_code": msg.error_code,
        "ref": msg.ref,
    }


class ContactIn(BaseModel):
    msisdn: str
    name: str | None = None


class ContactOut(ContactIn):
    id: int
    opt_out: bool

    class Config:
        orm_mode = True


@app.get("/api/contacts", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_session)):
    return db.query(Contact).all()


@app.post("/api/contacts", response_model=ContactOut)
def create_contact(contact: ContactIn, db: Session = Depends(get_session)):
    obj = Contact(msisdn=contact.msisdn, name=contact.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/api/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_session)):
    obj = db.get(Contact, contact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    return obj


@app.put("/api/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, contact: ContactIn, db: Session = Depends(get_session)):
    obj = db.get(Contact, contact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    obj.msisdn = contact.msisdn
    obj.name = contact.name
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_session)):
    obj = db.get(Contact, contact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}


class DeviceIn(BaseModel):
    name: str
    port: str
    active: bool = True


class DeviceOut(DeviceIn):
    id: int

    class Config:
        orm_mode = True


@app.get("/api/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_session)):
    return db.query(Device).all()


@app.post("/api/devices", response_model=DeviceOut)
def create_device(device: DeviceIn, db: Session = Depends(get_session)):
    obj = Device(**device.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/api/devices/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_session)):
    obj = db.get(Device, device_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    return obj


@app.put("/api/devices/{device_id}", response_model=DeviceOut)
def update_device(device_id: int, device: DeviceIn, db: Session = Depends(get_session)):
    obj = db.get(Device, device_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    obj.name = device.name
    obj.port = device.port
    obj.active = device.active
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_session)):
    obj = db.get(Device, device_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}


class CampaignIn(BaseModel):
    name: str
    template: str
    list_id: int
    start_time: datetime
    window: str | None = None
    rate_limit: int = 1


class CampaignOut(BaseModel):
    id: int
    name: str
    template: str
    list_id: int
    start_time: datetime
    window_start: str | None
    window_end: str | None
    rate_limit: int
    total: int
    sent: int
    delivered: int
    failed: int

    class Config:
        orm_mode = True


def send_campaign(campaign_id: int) -> None:
    db = SessionLocal()
    try:
        campaign = db.get(Campaign, campaign_id)
        if not campaign:
            return
        contacts = (
            db.query(Contact)
            .join(ListMember, ListMember.contact_id == Contact.id)
            .filter(
                ListMember.list_id == campaign.list_id, Contact.opt_out.is_(False)
            )
            .all()
        )
        devices = db.query(Device).filter(Device.active.is_(True)).all()
        if not devices:
            return
        cycle = itertools.cycle(devices)
        last_sent: dict[int, float] = {d.id: 0.0 for d in devices}
        seen: set[str] = set()
        for contact in contacts:
            if contact.msisdn in seen:
                continue
            seen.add(contact.msisdn)
            if campaign.window_start and campaign.window_end:
                ws = datetime.strptime(campaign.window_start, "%H:%M").time()
                we = datetime.strptime(campaign.window_end, "%H:%M").time()
                now = datetime.utcnow()
                if not (ws <= now.time() <= we):
                    target = datetime.combine(now.date(), ws)
                    if now.time() > we:
                        target += timedelta(days=1)
                    time.sleep((target - now).total_seconds())
            device = next(cycle)
            wait = max(0, last_sent[device.id] + 1.0 / campaign.rate_limit - time.time())
            if wait:
                time.sleep(wait)
            refs = send_sms(contact.msisdn, campaign.template, device.port)
            msg = Message(
                campaign_id=campaign.id,
                contact_id=contact.id,
                device_id=device.id,
                text=campaign.template,
                ref=refs[0] if refs else None,
                status="sent",
            )
            db.add(msg)
            db.commit()
            last_sent[device.id] = time.time()
    finally:
        db.close()


@app.post("/api/campaigns", response_model=CampaignOut)
def create_campaign(campaign: CampaignIn, db: Session = Depends(get_session)):
    window_start = window_end = None
    if campaign.window:
        parts = campaign.window.split("-")
        if len(parts) == 2:
            window_start, window_end = parts
    obj = Campaign(
        name=campaign.name,
        template=campaign.template,
        list_id=campaign.list_id,
        start_time=campaign.start_time,
        window_start=window_start,
        window_end=window_end,
        rate_limit=campaign.rate_limit,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    SCHEDULER.add_job(send_campaign, "date", run_date=campaign.start_time, args=[obj.id])
    total = db.query(ListMember).filter(ListMember.list_id == obj.list_id).count()
    return CampaignOut(
        id=obj.id,
        name=obj.name,
        template=obj.template,
        list_id=obj.list_id,
        start_time=obj.start_time,
        window_start=obj.window_start,
        window_end=obj.window_end,
        rate_limit=obj.rate_limit,
        total=total,
        sent=0,
        delivered=0,
        failed=0,
    )


@app.get("/api/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_session)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="not found")
    total = db.query(ListMember).filter(ListMember.list_id == campaign.list_id).count()
    sent = db.query(Message).filter(Message.campaign_id == campaign_id).count()
    delivered = (
        db.query(Message)
        .filter(Message.campaign_id == campaign_id, Message.status == "delivered")
        .count()
    )
    failed = (
        db.query(Message)
        .filter(Message.campaign_id == campaign_id, Message.status == "failed")
        .count()
    )
    return CampaignOut(
        id=campaign.id,
        name=campaign.name,
        template=campaign.template,
        list_id=campaign.list_id,
        start_time=campaign.start_time,
        window_start=campaign.window_start,
        window_end=campaign.window_end,
        rate_limit=campaign.rate_limit,
        total=total,
        sent=sent,
        delivered=delivered,
        failed=failed,
    )


@app.get("/api/inbox")
def api_inbox() -> list[dict]:
    return INBOX

