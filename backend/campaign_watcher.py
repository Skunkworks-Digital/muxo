"""Watch a folder for CSV campaign files and schedule sending."""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend.db import SessionLocal
from backend.models import Campaign, Contact, List, ListMember
from backend.utils import normalize_msisdn

WATCH_DIR = Path(__file__).resolve().parent.parent / "inbox" / "campaigns"


class _CampaignHandler(FileSystemEventHandler):
    def __init__(self, scheduler):
        super().__init__()
        self.scheduler = scheduler

    def on_created(self, event) -> None:  # pragma: no cover - filesystem events
        if event.is_directory or not event.src_path.endswith(".csv"):
            return
        path = Path(event.src_path)
        _process_csv(path, self.scheduler)


def _process_csv(path: Path, scheduler) -> None:
    from backend.main import send_campaign  # local import to avoid circular

    db = SessionLocal()
    try:
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return
        name = path.stem
        template = rows[0].get("text", "")
        contact_ids: list[int] = []
        list_obj = List(name=name)
        db.add(list_obj)
        db.commit()
        db.refresh(list_obj)
        for row in rows:
            msisdn_raw = row.get("msisdn", "")
            try:
                msisdn = normalize_msisdn(msisdn_raw)
            except ValueError as exc:
                logging.warning("invalid number %s in %s: %s", msisdn_raw, path, exc)
                continue
            contact = db.query(Contact).filter(Contact.msisdn == msisdn).first()
            if not contact:
                contact = Contact(msisdn=msisdn)
                db.add(contact)
                db.commit()
                db.refresh(contact)
            db.add(ListMember(list_id=list_obj.id, contact_id=contact.id))
            contact_ids.append(contact.id)
        db.commit()
        campaign = Campaign(
            name=name,
            template=template,
            list_id=list_obj.id,
            start_time=datetime.utcnow(),
            rate_limit=1,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        scheduler.add_job(
            send_campaign, "date", run_date=campaign.start_time, args=[campaign.id]
        )
    except Exception as exc:  # pragma: no cover - best effort
        logging.error("failed to process %s: %s", path, exc)
    finally:
        db.close()
        try:
            os.remove(path)
        except OSError:
            pass


def start_campaign_watcher(scheduler) -> Observer:
    os.makedirs(WATCH_DIR, exist_ok=True)
    handler = _CampaignHandler(scheduler)
    observer = Observer()
    observer.schedule(handler, str(WATCH_DIR), recursive=False)
    observer.daemon = True
    observer.start()
    return observer
