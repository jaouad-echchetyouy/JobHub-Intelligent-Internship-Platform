import logging
import threading

from .database import SessionLocal
from .models import Offer
from .notifier import notify_new_offers
from .scrapers import run_all

log = logging.getLogger(__name__)
_lock = threading.Lock()


def save_new_offers(db, items: list[dict]) -> list[Offer]:
    """Insère uniquement les offres dont l'URL est inconnue et les retourne."""
    existing = {u for (u,) in db.query(Offer.url)}
    new = []
    for item in items:
        if item["url"] in existing:
            continue
        existing.add(item["url"])
        offer = Offer(**item)
        db.add(offer)
        new.append(offer)
    db.commit()
    return new


def run_scrape() -> dict:
    """Scrape toutes les sources, enregistre les nouveautés, notifie les abonnés."""
    if not _lock.acquire(blocking=False):
        return {"fetched": 0, "new": 0, "emails": 0, "report": {}, "busy": True}
    try:
        items, report = run_all()
        with SessionLocal() as db:
            new = save_new_offers(db, items)
            emails = notify_new_offers(db, new)
        log.info("Scraping : %s récupérées, %s nouvelles, %s emails", len(items), len(new), emails)
        return {"fetched": len(items), "new": len(new), "emails": emails, "report": report, "busy": False}
    finally:
        _lock.release()
