"""Sources d'offres. On privilégie des APIs publiques (stables) plutôt que du HTML fragile.

Pour ajouter une source : écris une fonction fetch_xxx() qui retourne une liste de dicts
(via make_offer) et ajoute-la dans SOURCES.
"""
import html
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from .skills import extract_skills

load_dotenv()

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (JobHub student project)"}
_TAG = re.compile(r"<[^>]+>")


def clean(text: str, limit: int = 3000) -> str:
    text = html.unescape(_TAG.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def detect_type(title: str) -> str:
    t = (title or "").lower()
    if "hackathon" in t:
        return "Hackathon"
    keys = ("intern", "stage", "trainee", "apprenti", "working student", "werkstudent", "praktikum", "graduate")
    return "Internship" if any(k in t for k in keys) else "Job"


def detect_mode(location: str, remote: bool = False) -> str:
    loc = (location or "").lower()
    if remote or any(k in loc for k in ("remote", "anywhere", "worldwide")):
        return "Remote"
    return "Hybrid" if "hybrid" in loc else "On-site"


def _date(value) -> datetime | None:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None)
        if isinstance(value, str) and value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, OSError):
        pass
    return None


def make_offer(title, company, location, description, url, tags, source, posted=None, remote=False) -> dict:
    description = clean(description)
    skills = extract_skills(f"{title} {' '.join(tags or [])} {description}")
    return {
        "title": clean(title, 300),
        "company": clean(company, 200),
        "location": clean(location, 200) or ("Remote" if remote else ""),
        "work_mode": detect_mode(location, remote),
        "job_type": detect_type(title),
        "description": description,
        "skills": ",".join(skills),
        "url": url,
        "source": source,
        "posted_at": _date(posted),
    }


def fetch_remotive() -> list[dict]:
    out = []
    for q in ("intern", "software", "data"):
        r = requests.get(
            "https://remotive.com/api/remote-jobs", params={"search": q, "limit": 40}, headers=HEADERS, timeout=20
        )
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            out.append(
                make_offer(
                    j.get("title"), j.get("company_name"), j.get("candidate_required_location"),
                    j.get("description"), j.get("url"), j.get("tags"), "Remotive",
                    j.get("publication_date"), remote=True,
                )
            )
    return out


def fetch_arbeitnow() -> list[dict]:
    r = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=HEADERS, timeout=20)
    r.raise_for_status()
    return [
        make_offer(
            j.get("title"), j.get("company_name"), j.get("location"), j.get("description"),
            j.get("url"), j.get("tags"), "Arbeitnow", j.get("created_at"), remote=bool(j.get("remote")),
        )
        for j in r.json().get("data", [])
    ]


def fetch_remoteok() -> list[dict]:
    r = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()[1:]  # le 1er élément est un avis légal
    return [
        make_offer(
            j.get("position"), j.get("company"), j.get("location") or "Remote", j.get("description"),
            j.get("url") or j.get("apply_url"), j.get("tags"), "RemoteOK", j.get("date"), remote=True,
        )
        for j in data
        if j.get("position")
    ]


def fetch_jooble() -> list[dict]:
    """Offres au Maroc via l'API Jooble. Nécessite JOOBLE_API_KEY dans .env (gratuit)."""
    key = os.getenv("JOOBLE_API_KEY")
    if not key:
        log.info("JOOBLE_API_KEY absente : source Jooble ignorée.")
        return []
    out = []
    for kw in ("stage", "internship", "stagiaire"):
        r = requests.post(
            f"https://jooble.org/api/{key}",
            json={"keywords": kw, "location": "Maroc"},
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            out.append(
                make_offer(
                    j.get("title"), j.get("company"), j.get("location"), j.get("snippet"),
                    j.get("link"), [], "Jooble", j.get("updated"),
                )
            )
    return out


SOURCES = {
    "Remotive": fetch_remotive,
    "Arbeitnow": fetch_arbeitnow,
    "RemoteOK": fetch_remoteok,
    "Jooble": fetch_jooble,
}


def is_alive(url: str) -> bool:
    """Faux seulement si le lien est mort (404/410) ou injoignable."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True, stream=True)
        r.close()
        return r.status_code not in (404, 410)
    except requests.Timeout:
        return True  # doute : on garde l'offre
    except requests.RequestException:
        return False


def run_all() -> tuple[list[dict], dict]:
    """Retourne (offres dédupliquées et encore en ligne, rapport par source)."""
    items, seen, report = [], set(), {}
    for name, fn in SOURCES.items():
        try:
            fetched = [o for o in fn() if o.get("url") and o.get("title")]
            report[name] = {"ok": True, "count": len(fetched)}
            for o in fetched:
                if o["url"] not in seen:
                    seen.add(o["url"])
                    items.append(o)
        except Exception as exc:  # une source en panne ne doit pas bloquer les autres
            log.warning("Scraper %s en échec : %s", name, exc)
            report[name] = {"ok": False, "error": str(exc)[:160]}

    # On écarte les offres dont le lien n'existe plus (404/410)
    with ThreadPoolExecutor(max_workers=8) as pool:
        alive = list(pool.map(lambda o: is_alive(o["url"]), items))
    removed = alive.count(False)
    items = [o for o, ok in zip(items, alive) if ok]
    log.info("Liens morts écartés : %d", removed)
    return items, report