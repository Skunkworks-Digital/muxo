"""Inbound SMS receiving and simple auto-reply rules."""

from __future__ import annotations

import logging
import threading
import time

import serial

from backend.db import SessionLocal
from backend.models import Contact, Message
from backend.sms.pdu import parse_cds, parse_pdu
from backend.sms.sender import send_sms
from backend.sms.store import INBOX
from backend.utils import normalize_msisdn, notify_status

INFO_TEMPLATE = "Thanks for your message."


def _handle_inbound(
    msisdn: str, text: str, device_id: str, port: serial.Serial
) -> None:
    db = SessionLocal()
    try:
        try:
            norm = normalize_msisdn(msisdn)
        except ValueError as exc:
            logging.warning("invalid inbound number %s: %s", msisdn, exc)
            return
        contact = db.query(Contact).filter(Contact.msisdn == norm).first()
        if not contact:
            contact = Contact(msisdn=norm)
            db.add(contact)
            db.commit()
            db.refresh(contact)
        INBOX.append({"msisdn": norm, "text": text, "device_id": device_id})
        keyword = text.strip().upper()
        if keyword == "STOP":
            contact.opt_out = True
            db.commit()
        elif keyword == "INFO" and not contact.opt_out:
            try:
                send_sms(msisdn, INFO_TEMPLATE, device_id, port=port)
            except Exception as exc:  # pragma: no cover - hardware dependent
                logging.warning("auto-reply failed: %s", exc)
    finally:
        db.close()


def _handle_dlr(ref: str, status: int) -> None:
    db = SessionLocal()
    try:
        msg = db.query(Message).filter(Message.ref == ref).first()
        if msg:
            if status < 0x20:
                msg.status = "delivered"
            elif status >= 0x40:
                msg.status = "failed"
                msg.error_code = f"{status:02X}"
            else:
                msg.status = "unknown"
            db.commit()
            notify_status(
                {
                    "id": msg.id,
                    "msisdn": msg.contact.msisdn,
                    "status": msg.status,
                    "error_code": msg.error_code,
                }
            )
    finally:
        db.close()


def _reader(device_id: str, baud: int = 115200) -> None:
    while True:
        try:
            with serial.Serial(device_id, baudrate=baud, timeout=5) as port:
                port.write(b"AT+CMGF=0\r")
                port.readline()
                port.write(b"AT+CNMI=2,2,0,0,0\r")
                port.readline()
                while True:
                    line = port.readline().decode(errors="ignore").strip()
                    if line.startswith("+CMT:"):
                        pdu_line = port.readline().decode(errors="ignore").strip()
                        try:
                            msisdn, text = parse_pdu(pdu_line)
                            _handle_inbound(msisdn, text, device_id, port)
                        except Exception as exc:  # pragma: no cover - best effort
                            logging.warning("parse error: %s", exc)
                    elif line.startswith("+CDS:"):
                        pdu_line = port.readline().decode(errors="ignore").strip()
                        try:
                            ref, status = parse_cds(pdu_line)
                            _handle_dlr(ref, status)
                        except Exception as exc:  # pragma: no cover - best effort
                            logging.warning("dlr parse error: %s", exc)
                    elif not line:
                        # Poll fallback
                        port.write(b"AT+CMGL=4\r")
                        time.sleep(1)
                        break
        except Exception as exc:  # pragma: no cover - hardware dependent
            logging.warning("receiver error on %s: %s", device_id, exc)
            time.sleep(2)


def start_receiver(device_id: str, baud: int = 115200) -> threading.Thread:
    thread = threading.Thread(target=_reader, args=(device_id, baud), daemon=True)
    thread.start()
    return thread
