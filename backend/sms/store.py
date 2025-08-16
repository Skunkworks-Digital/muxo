"""In-memory storage for SMS messages and contacts."""

from __future__ import annotations

INBOX: list[dict] = []
OUTBOX: list[dict] = []
CONTACTS: dict[str, dict] = {}
