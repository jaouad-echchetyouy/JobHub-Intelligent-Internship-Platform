from apscheduler.schedulers.background import BackgroundScheduler

from .config import SCRAPE_INTERVAL_HOURS
from .service import run_scrape

_scheduler = BackgroundScheduler(daemon=True)


def start_scheduler():
    if not _scheduler.running:
        _scheduler.add_job(run_scrape, "interval", hours=SCRAPE_INTERVAL_HOURS, id="scrape", replace_existing=True)
        _scheduler.start()


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
