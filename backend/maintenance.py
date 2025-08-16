"""Maintenance tasks such as backups and data retention."""

import logging
import os
import shutil
from datetime import datetime, timedelta

from backend.db import DATABASE_URL, SessionLocal
from backend.models import Audit, Message

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")


def backup_db() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    db_path = DATABASE_URL.replace("sqlite:///", "")
    target = os.path.join(BACKUP_DIR, f"muxo-{timestamp}.db")
    shutil.copy(db_path, target)
    return target


def purge_old_data() -> None:
    db = SessionLocal()
    try:
        msg_cutoff = datetime.utcnow() - timedelta(days=90)
        db.query(Message).filter(Message.created_at < msg_cutoff).delete()
        audit_cutoff = datetime.utcnow() - timedelta(days=365)
        db.query(Audit).filter(Audit.timestamp < audit_cutoff).delete()
        db.commit()
    finally:
        db.close()


def nightly_backup() -> None:
    path = backup_db()
    purge_old_data()
    logging.info("nightly backup saved to %s", path)


if __name__ == "__main__":
    nightly_backup()
