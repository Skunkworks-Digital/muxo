"""Utility helpers for MSISDN normalization and webhooks."""

from __future__ import annotations

import logging
import os
from typing import Optional

import phonenumbers
import requests
from phonenumbers import NumberParseException, PhoneNumberFormat

DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "US")
STATUS_WEBHOOK_URL = os.getenv("STATUS_WEBHOOK_URL")


def normalize_msisdn(msisdn: str) -> str:
    """Normalize a phone number to E.164 format using default country.

    Raises ValueError if the number is invalid.
    """
    try:
        num = phonenumbers.parse(msisdn, DEFAULT_COUNTRY)
    except NumberParseException as exc:  # pragma: no cover - library errors
        raise ValueError(str(exc)) from exc
    if not phonenumbers.is_valid_number(num):
        raise ValueError("invalid msisdn")
    return phonenumbers.format_number(num, PhoneNumberFormat.E164)


def notify_status(payload: dict) -> None:
    """POST a status update to the configured webhook if set."""
    url: Optional[str] = STATUS_WEBHOOK_URL
    if not url:
        return
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as exc:  # pragma: no cover - network errors
        logging.warning("webhook post failed: %s", exc)
