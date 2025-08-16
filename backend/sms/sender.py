"""SMS sending via AT commands with segmentation support."""

from __future__ import annotations

import logging
from typing import List

import serial

from backend.sms.pdu import build_pdus
from backend.sms.store import OUTBOX


def send_sms(
    msisdn: str,
    text: str,
    device_id: str,
    baud: int = 115200,
    port: serial.Serial | None = None,
) -> List[str]:
    """Send an SMS, handling long-message segmentation.

    Returns list of message references reported by the modem.
    """

    close_port = False
    if port is None:
        port = serial.Serial(device_id, baudrate=baud, timeout=5)
        close_port = True
    try:
        pdus = build_pdus(msisdn, text)
        refs: list[str] = []
        port.write(b"AT+CMGF=0\r")
        port.readline()
        for seg in pdus:
            pdu = seg["pdu"]
            tpdu_length = (len(pdu) // 2) - 1
            logging.info("sending PDU %s", pdu)
            port.write(f"AT+CMGS={tpdu_length}\r".encode())
            port.readline()
            port.write(bytes.fromhex(pdu) + b"\x1a")
            ref = ""
            while True:
                line = port.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("+CMGS:"):
                    ref = line.split(":")[1].strip()
                if line in {"OK", "ERROR"} or line.startswith("+CMS ERROR"):
                    if line != "OK":
                        raise RuntimeError(line)
                    break
            refs.append(ref)
            OUTBOX.append(
                {
                    "msisdn": msisdn,
                    "text": seg["text"],
                    "device_id": device_id,
                    "seg_total": seg["seg_total"],
                    "seg_index": seg["seg_index"],
                    "ref": ref,
                }
            )
        return refs
    finally:
        if close_port:
            port.close()
