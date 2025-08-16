"""Serial modem probing utilities."""

from __future__ import annotations

import glob
import logging
from typing import Any

import serial
from serial import SerialException


def _send_command(port: serial.Serial, command: str) -> list[str]:
    port.write((command + "\r").encode())
    lines: list[str] = []
    while True:
        line = port.readline().decode(errors="ignore").strip()
        if not line:
            break
        lines.append(line)
        if line in {"OK", "ERROR"}:
            break
    return lines


def probe_modems(baud: int = 115200, timeout: float = 1.0) -> list[dict[str, Any]]:
    """Probe /dev/ttyUSB* ports for AT-capable modems."""
    devices: list[dict[str, Any]] = []
    for path in glob.glob("/dev/ttyUSB*"):
        try:
            with serial.Serial(path, baudrate=baud, timeout=timeout) as port:
                at = _send_command(port, "AT")
                if not at or at[-1] != "OK":
                    continue
                model_resp = _send_command(port, "AT+CGMM")
                csq_resp = _send_command(port, "AT+CSQ")
                cpin_resp = _send_command(port, "AT+CPIN?")

                model = model_resp[0] if model_resp else ""
                signal = None
                if csq_resp:
                    try:
                        rssi = int(csq_resp[0].split(":")[1].split(",")[0].strip())
                        signal = None if rssi == 99 else rssi
                    except Exception:  # pragma: no cover - best effort
                        signal = None
                sim_ready = bool(cpin_resp and "+CPIN: READY" in cpin_resp[0].upper())
                devices.append(
                    {
                        "port": path,
                        "model": model,
                        "signal": signal,
                        "sim_ready": sim_ready,
                    }
                )
        except SerialException as exc:  # pragma: no cover - hardware dependent
            logging.warning("probe failed for %s: %s", path, exc)
        except Exception as exc:  # pragma: no cover - best effort
            logging.warning("unexpected error for %s: %s", path, exc)
    return devices
