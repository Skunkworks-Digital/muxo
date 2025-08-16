"""Inbound SMS receiving and simple auto-reply rules."""

from __future__ import annotations

import logging
import threading
import time

import serial

from backend.sms.pdu import parse_pdu
from backend.sms.sender import send_sms
from backend.sms.store import CONTACTS, INBOX

INFO_TEMPLATE = "Thanks for your message."


def _handle_inbound(
    msisdn: str, text: str, device_id: str, port: serial.Serial
) -> None:
    INBOX.append({"msisdn": msisdn, "text": text, "device_id": device_id})
    keyword = text.strip().upper()
    if keyword == "STOP":
        CONTACTS.setdefault(msisdn, {})["opt_out"] = True
    elif keyword == "INFO":
        if not CONTACTS.get(msisdn, {}).get("opt_out"):
            try:
                send_sms(msisdn, INFO_TEMPLATE, device_id, port=port)
            except Exception as exc:  # pragma: no cover - hardware dependent
                logging.warning("auto-reply failed: %s", exc)


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
