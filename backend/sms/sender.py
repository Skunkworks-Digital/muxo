"""SMS sending via AT commands."""

from __future__ import annotations

import logging

import serial

from backend.sms.pdu import build_pdu


def send_sms(msisdn: str, text: str, device_id: str, baud: int = 115200) -> str:
    """Send a single SMS via the given serial device.

    Returns the message reference reported by the modem.
    """
    pdu = build_pdu(msisdn, text)
    tpdu_length = (len(pdu) // 2) - 1  # exclude SMSC length octet
    logging.info("sending PDU %s", pdu)
    with serial.Serial(device_id, baudrate=baud, timeout=5) as port:
        port.write(b"AT+CMGF=0\r")
        port.readline()
        port.write(f"AT+CMGS={tpdu_length}\r".encode())
        port.readline()
        port.write(bytes.fromhex(pdu) + b"\x1A")
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
    return ref
