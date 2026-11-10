import logging
import smtplib
from email.message import EmailMessage
from html import escape

from . import config
from .models import User
from .recommender import score_offers

log = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str, text_body: str) -> bool:
    if not config.EMAIL_USER or not config.EMAIL_PASS or "example.com" in config.EMAIL_USER:
        log.info("Email non configuré — message pour %s ignoré : %s", to, subject)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.EMAIL_USER, to, subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(config.EMAIL_USER, config.EMAIL_PASS)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        log.warning("Envoi email échoué pour %s : %s", to, exc)
        return False


def notify_new_offers(db, new_offers) -> int:
    """Envoie à chaque abonné les nouvelles offres dont le score dépasse son seuil."""
    if not new_offers:
        return 0
    sent = 0
    for user in db.query(User).filter(User.notify.is_(True)).all():
        picks = [s for s in score_offers(user, new_offers) if s["score"] >= (user.min_score or 0)][:10]
        if not picks:
            continue
        rows = "".join(
            f"<li style='margin-bottom:10px'><a href='{escape(p['offer'].url)}'><b>{escape(p['offer'].title)}</b></a>"
            f" — {escape(p['offer'].company or '')} <span style='color:#6c47ff'>({p['score']} %)</span></li>"
            for p in picks
        )
        html_body = (
            f"<div style='font-family:Arial,sans-serif'><h2>Bonjour {escape(user.first_name)},</h2>"
            f"<p>{len(picks)} nouvelle(s) offre(s) correspondent à ton profil :</p><ul>{rows}</ul></div>"
        )
        text_body = "\n".join(f"- {p['offer'].title} ({p['offer'].company}) {p['score']}% : {p['offer'].url}" for p in picks)
        if send_email(user.email, f"{len(picks)} nouvelle(s) offre(s) pour toi", html_body, text_body):
            sent += 1
    return sent
