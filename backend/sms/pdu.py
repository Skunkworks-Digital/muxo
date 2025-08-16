"""SMS PDU helpers for encoding, segmentation and decoding."""

from __future__ import annotations

import random
from typing import List, Tuple

GSM_7BIT_BASIC = {chr(i) for i in range(32, 127)} | {"\n", "\r", "\f", "\b", "\t"}


def _encode_number(number: str) -> Tuple[str, str, int]:
    if number.startswith("+"):
        number = number[1:]
        toa = "91"
    else:
        toa = "81"
    digits = number
    if len(digits) % 2 == 1:
        digits += "F"
    swapped = "".join(digits[i + 1] + digits[i] for i in range(0, len(digits), 2))
    return toa, swapped, len(number)


def _encode_gsm7(text: str, udh: bytes | None = None) -> Tuple[str, int]:
    data = bytearray()
    carry = 0
    carry_bits = 0

    def push(byte: int) -> None:
        nonlocal carry, carry_bits
        data.append(((byte << carry_bits) & 0xFF) | carry)
        carry = byte >> (8 - carry_bits)
        carry_bits += 1
        if carry_bits == 8:
            data.append(carry)
            carry = 0
            carry_bits = 0

    if udh:
        for b in udh:
            push(b)
    for ch in text:
        push(ord(ch) & 0x7F)
    if carry_bits:
        data.append(carry)
    if udh:
        udl = len(data)
    else:
        udl = len(text)
    return data.hex().upper(), udl


def _encode_ucs2(text: str, udh: bytes | None = None) -> Tuple[str, int]:
    data = text.encode("utf-16-be")
    if udh:
        data = udh + data
    return data.hex().upper(), len(data)


def _segment_text(text: str, encoding: str) -> List[str]:
    if encoding == "gsm7":
        limit = 160
        part = 153
    else:
        limit = 70
        part = 67
    if len(text) <= limit:
        return [text]
    return [text[i : i + part] for i in range(0, len(text), part)]


def build_pdus(msisdn: str, text: str) -> list[dict[str, object]]:
    """Build PDUs for the given text, handling segmentation."""
    encoding = "gsm7" if all(ch in GSM_7BIT_BASIC for ch in text) else "ucs2"
    segments = _segment_text(text, encoding)
    ref = random.randint(0, 255) if len(segments) > 1 else None
    toa, number, length = _encode_number(msisdn)
    dcs = "00" if encoding == "gsm7" else "08"
    pdus: list[dict[str, object]] = []
    for idx, segment in enumerate(segments, start=1):
        udh = (
            bytes([5, 0, 3, ref or 0, len(segments), idx]) if ref is not None else None
        )
        if encoding == "gsm7":
            ud, udl = _encode_gsm7(segment, udh)
        else:
            ud, udl = _encode_ucs2(segment, udh)
        first_octet = "41" if udh else "01"
        pdu = (
            "00"
            + first_octet
            + "00"
            + f"{length:02X}"
            + toa
            + number
            + "00"
            + dcs
            + f"{udl:02X}"
            + ud
        )
        pdus.append(
            {"pdu": pdu, "seg_total": len(segments), "seg_index": idx, "text": segment}
        )
    return pdus


def _decode_gsm7(data: bytes, udhl: int = 0) -> str:
    bits = 0
    carry = 0
    septets: list[int] = []
    for byte in data:
        septets.append(((byte << bits) & 0x7F) | carry)
        carry = byte >> (7 - bits)
        bits += 1
        if bits == 7:
            septets.append(carry & 0x7F)
            carry = 0
            bits = 0
    text = "".join(chr(s) for s in septets)
    if udhl:
        skip = ((udhl + 1) * 8 + 6) // 7
        text = text[skip:]
    return text.rstrip("\x00")


def parse_pdu(pdu: str) -> Tuple[str, str]:
    """Parse an inbound PDU returning (msisdn, text)."""
    i = 0
    smsc_len = int(pdu[i : i + 2], 16)
    i += 2 + smsc_len * 2
    first = int(pdu[i : i + 2], 16)
    i += 2
    addr_len = int(pdu[i : i + 2], 16)
    i += 2
    toa = pdu[i : i + 2]
    i += 2
    addr_field_len = addr_len + (addr_len % 2)
    number = pdu[i : i + addr_field_len]
    i += addr_field_len
    msisdn = "".join(
        number[j + 1] + number[j] for j in range(0, len(number), 2)
    ).rstrip("F")
    if toa == "91":
        msisdn = "+" + msisdn
    i += 2  # PID
    dcs = pdu[i : i + 2]
    i += 2
    i += 14  # timestamp
    i += 2  # UDL
    ud_bytes = bytes.fromhex(pdu[i:])
    udhi = bool(first & 0x40)
    if dcs == "00":
        if udhi:
            udhl = ud_bytes[0]
            text = _decode_gsm7(ud_bytes, udhl)
        else:
            text = _decode_gsm7(ud_bytes)
    else:
        if udhi:
            udhl = ud_bytes[0]
            text = ud_bytes[udhl + 1 :].decode("utf-16-be")
        else:
            text = ud_bytes.decode("utf-16-be")
    return msisdn, text


def parse_cds(pdu: str) -> Tuple[str, int]:
    """Parse a delivery report PDU returning (reference, status)."""
    i = 0
    smsc_len = int(pdu[i : i + 2], 16)
    i += 2 + smsc_len * 2
    i += 2  # first octet
    ref = pdu[i : i + 2]
    i += 2
    addr_len = int(pdu[i : i + 2], 16)
    i += 2
    i += 2  # TOA
    addr_field_len = addr_len + (addr_len % 2)
    i += addr_field_len
    i += 14  # SCTS
    i += 14  # discharge time
    status = int(pdu[i : i + 2], 16)
    return ref.lstrip("0"), status
