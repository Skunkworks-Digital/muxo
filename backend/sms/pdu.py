"""Simple SMS PDU builder supporting GSM 7-bit and UCS-2."""

from __future__ import annotations

from typing import Tuple

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


def _encode_gsm7(text: str) -> Tuple[str, int]:
    data = bytearray()
    carry = 0
    carry_bits = 0
    for ch in text:
        val = ord(ch) & 0x7F
        byte = ((val << carry_bits) & 0xFF) | carry
        data.append(byte)
        carry = val >> (8 - carry_bits)
        carry_bits += 1
        if carry_bits == 8:
            data.append(carry)
            carry = 0
            carry_bits = 0
    if carry_bits:
        data.append(carry)
    return data.hex().upper(), len(text)


def _encode_ucs2(text: str) -> Tuple[str, int]:
    data = text.encode("utf-16-be")
    return data.hex().upper(), len(data)


def build_pdu(msisdn: str, text: str) -> str:
    toa, number, length = _encode_number(msisdn)
    if all(ch in GSM_7BIT_BASIC for ch in text):
        ud, udl = _encode_gsm7(text)
        dcs = "00"
    else:
        ud, udl = _encode_ucs2(text)
        dcs = "08"
    first_octet = "01"
    pdu = (
        "00"  # SMSC
        + first_octet
        + "00"  # MR
        + f"{length:02X}"
        + toa
        + number
        + "00"  # PID
        + dcs
        + f"{udl:02X}"
        + ud
    )
    return pdu
