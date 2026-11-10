import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


SECRET_KEY = env("SECRET_KEY", "dev-secret-change-me")
DATABASE_URL = env("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'jobhub.db').as_posix()}")
USE_DEMO = env("USE_DEMO", "1") == "1"
SCRAPE_INTERVAL_HOURS = int(env("SCRAPE_INTERVAL_HOURS", "6") or 6)

EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(env("EMAIL_PORT", "587") or 587)
EMAIL_USER = env("EMAIL_USER")
EMAIL_PASS = env("EMAIL_PASS")

ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-sonnet-4-5")
