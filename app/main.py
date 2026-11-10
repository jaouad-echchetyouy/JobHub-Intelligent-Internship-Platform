import threading
from collections import Counter
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from starlette.middleware.sessions import SessionMiddleware

from . import chatbot
from .config import BASE_DIR, SECRET_KEY, USE_DEMO
from .database import Base, SessionLocal, engine, get_db
from .demo_data import load_demo
from .models import Offer, SavedOffer, User, split_csv, utcnow
from .recommender import score_offers
from .scheduler import start_scheduler, stop_scheduler
from .security import hash_password, verify_password
from .service import run_scrape
from .skills import SKILLS

APP_DIR = BASE_DIR / "app"
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.query(Offer.id).first() is None:
            if USE_DEMO:
                load_demo(db)
            else:
                threading.Thread(target=run_scrape, daemon=True).start()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="JobHub", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60 * 60 * 24 * 14, same_site="lax")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


# ---------- Authentification ----------
class NotAuthenticated(Exception):
    pass


@app.exception_handler(NotAuthenticated)
async def _redirect_login(request: Request, exc: NotAuthenticated):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Connexion requise"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


def current_user(request: Request, db=Depends(get_db)) -> User:
    uid = request.session.get("uid")
    user = db.get(User, uid) if uid else None
    if not user:
        raise NotAuthenticated()
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise NotAuthenticated()
    return user


def page(request: Request, name: str, user: User | None, active: str = "", **ctx):
    return templates.TemplateResponse(request, name, {"user": user, "active": active, **ctx})


def clean_skills(raw: str) -> str:
    seen, out = set(), []
    for s in split_csv(raw.replace(";", ",").replace("\n", ",")):
        if s not in seen:
            seen.add(s)
            out.append(s)
    return ",".join(out)


# ---------- Helpers ----------
def offer_dict(o: Offer, saved_ids: set[int]) -> dict:
    return {
        "id": o.id, "title": o.title, "company": o.company, "location": o.location,
        "mode": o.work_mode, "type": o.job_type, "description": (o.description or "")[:1800],
        "url": o.url, "source": o.source, "skills": o.skill_list, "saved": o.id in saved_ids,
        "posted": (o.posted_at or o.created_at).strftime("%d/%m/%Y") if (o.posted_at or o.created_at) else "",
    }


def saved_ids_of(db, user) -> set[int]:
    return {oid for (oid,) in db.query(SavedOffer.offer_id).filter_by(user_id=user.id)}


def recent_offers(db, limit=600):
    return db.query(Offer).order_by(Offer.created_at.desc()).limit(limit).all()


def explanation(r: dict) -> str:
    parts = [f"Compétences : {r['skills_pct']} %", f"Profil : {r['text_pct']} %", f"Préférences : {r['pref_pct']} %"]
    txt = " · ".join(parts)
    if r["matching"]:
        txt += f". Tu maîtrises déjà : {', '.join(r['matching'])}"
    if r["missing"]:
        txt += f". À développer : {', '.join(r['missing'])}"
    return txt + "."


# ---------- Pages publiques ----------
@app.get("/")
def home(request: Request):
    return RedirectResponse("/dashboard" if request.session.get("uid") else "/login", status_code=303)


@app.get("/login")
def login_page(request: Request):
    return page(request, "login.html", None, error=None, email="")


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    email = email.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if not user or not verify_password(password, user.password_hash):
        return page(request, "login.html", None, error="Email ou mot de passe incorrect.", email=email)
    request.session["uid"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/register")
def register_page(request: Request):
    return page(request, "register.html", None, error=None, form={}, suggestions=SKILLS[:24])


@app.post("/register")
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...),
    skills: str = Form(""),
    db=Depends(get_db),
):
    form = {"full_name": full_name, "email": email, "skills": skills}
    email = email.strip().lower()
    error = None
    if len(full_name.strip()) < 2:
        error = "Entre ton nom complet."
    elif "@" not in email or "." not in email.split("@")[-1]:
        error = "Adresse email invalide."
    elif len(password) < 8:
        error = "Le mot de passe doit contenir au moins 8 caractères."
    elif password != confirm:
        error = "Les mots de passe ne correspondent pas."
    elif db.query(User.id).filter_by(email=email).first():
        error = "Un compte existe déjà avec cet email."
    if error:
        return page(request, "register.html", None, error=error, form=form, suggestions=SKILLS[:24])

    first = db.query(User.id).first() is None  # le 1er compte devient administrateur
    user = User(
        email=email, full_name=full_name.strip(), password_hash=hash_password(password),
        skills=clean_skills(skills), is_admin=first,
    )
    db.add(user)
    db.commit()
    request.session["uid"] = user.id
    return RedirectResponse("/profile?welcome=1" if not user.skill_list else "/dashboard", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------- Tableau de bord ----------
def build_stats(db, user: User, ranked: list[dict]) -> dict:
    now = utcnow()
    total = db.query(func.count(Offer.id)).scalar() or 0
    new24 = db.query(func.count(Offer.id)).filter(Offer.created_at >= now - timedelta(hours=24)).scalar() or 0
    saved = db.query(func.count(SavedOffer.id)).filter_by(user_id=user.id).scalar() or 0
    top = [r["score"] for r in ranked[:10]]

    by_source = dict(db.query(Offer.source, func.count(Offer.id)).group_by(Offer.source).all())
    by_type = dict(db.query(Offer.job_type, func.count(Offer.id)).group_by(Offer.job_type).all())

    days = Counter(d.created_at.date() for d in db.query(Offer.created_at).filter(Offer.created_at >= now - timedelta(days=14)))
    labels = [(now - timedelta(days=i)).date() for i in range(13, -1, -1)]
    per_day = {"labels": [d.strftime("%d/%m") for d in labels], "values": [days.get(d, 0) for d in labels]}

    skills = Counter(s for o in recent_offers(db) for s in o.skill_list).most_common(8)
    return {
        "kpis": {"total": total, "new24": new24, "saved": saved, "avg": round(sum(top) / len(top)) if top else 0},
        "by_source": by_source, "by_type": by_type, "per_day": per_day,
        "top_skills": {"labels": [s for s, _ in skills], "values": [c for _, c in skills]},
    }


@app.get("/dashboard")
def dashboard(request: Request, user: User = Depends(current_user), db=Depends(get_db)):
    ranked = score_offers(user, recent_offers(db))
    saved = saved_ids_of(db, user)
    top = [{**offer_dict(r["offer"], saved), "score": r["score"]} for r in ranked[:5]]
    return page(request, "dashboard.html", user, "dashboard", stats=build_stats(db, user, ranked), top=top)


# ---------- Recommandations ----------
@app.get("/recommendations")
def recommendations(request: Request, user: User = Depends(current_user)):
    return page(request, "recommendations.html", user, "recommendations")


@app.get("/api/recommendations")
def api_recommendations(
    q: str = "", type: str = "", mode: str = "", user: User = Depends(current_user), db=Depends(get_db)
):
    offers = recent_offers(db)
    if q:
        ql = q.lower()
        offers = [o for o in offers if ql in f"{o.title} {o.company} {o.skills}".lower()]
    if type:
        offers = [o for o in offers if o.job_type == type]
    if mode:
        offers = [o for o in offers if o.work_mode == mode]
    ranked = score_offers(user, offers)[:60]
    saved = saved_ids_of(db, user)
    return {
        "has_profile": bool(user.skill_list),
        "total": len(offers),
        "items": [
            {
                **offer_dict(r["offer"], saved), "score": r["score"], "skills_pct": r["skills_pct"],
                "text_pct": r["text_pct"], "pref_pct": r["pref_pct"], "matching": r["matching"],
                "missing": r["missing"], "why": explanation(r),
            }
            for r in ranked
        ],
    }


# ---------- Explorer toutes les offres ----------
PAGE_SIZE = 24


@app.get("/offers")
def offers_page(request: Request, user: User = Depends(current_user), db=Depends(get_db)):
    qp = request.query_params
    q, types, modes = qp.get("q", "").strip(), qp.getlist("type"), qp.getlist("mode")
    only_saved = qp.get("saved") == "1"
    raw_page = qp.get("page", "1")
    page_no = int(raw_page) if raw_page.isdigit() and int(raw_page) > 0 else 1

    query = db.query(Offer)
    if q:
        like = f"%{q}%"
        query = query.filter(Offer.title.ilike(like) | Offer.company.ilike(like) | Offer.skills.ilike(like))
    if types:
        query = query.filter(Offer.job_type.in_(types))
    if modes:
        query = query.filter(Offer.work_mode.in_(modes))
    if only_saved:
        query = query.join(SavedOffer, SavedOffer.offer_id == Offer.id).filter(SavedOffer.user_id == user.id)

    total = query.count()
    rows = query.order_by(Offer.created_at.desc()).offset((page_no - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    saved = saved_ids_of(db, user)
    return page(
        request, "offers.html", user, "saved" if only_saved else "offers",
        offers=[offer_dict(o, saved) for o in rows], total=total, q=q, types=types, modes=modes,
        only_saved=only_saved, page_no=page_no, pages=max(1, -(-total // PAGE_SIZE)),
    )


@app.post("/api/save/{offer_id}")
def toggle_save(offer_id: int, user: User = Depends(current_user), db=Depends(get_db)):
    if not db.get(Offer, offer_id):
        return JSONResponse({"error": "Offre introuvable"}, status_code=404)
    existing = db.query(SavedOffer).filter_by(user_id=user.id, offer_id=offer_id).first()
    if existing:
        db.delete(existing)
        saved = False
    else:
        db.add(SavedOffer(user_id=user.id, offer_id=offer_id))
        saved = True
    db.commit()
    return {"saved": saved}


# ---------- Chatbot ----------
@app.get("/chat")
def chat_page(request: Request, user: User = Depends(current_user), db=Depends(get_db)):
    ranked = score_offers(user, recent_offers(db))
    return page(request, "chat.html", user, "chat", ai_on=bool(chatbot.config.ANTHROPIC_API_KEY),
                top=[{"title": r["offer"].title, "score": r["score"]} for r in ranked[:3]])


@app.post("/api/chat")
async def api_chat(request: Request, user: User = Depends(current_user), db=Depends(get_db)):
    data = await request.json()
    question = str(data.get("message", "")).strip()[:1000]
    if not question:
        return JSONResponse({"error": "Message vide"}, status_code=400)
    ranked = score_offers(user, recent_offers(db))
    return chatbot.reply(question, user, ranked, data.get("history"))


# ---------- Profil ----------
@app.get("/profile")
def profile_page(request: Request, user: User = Depends(current_user)):
    return page(request, "profile.html", user, "profile", suggestions=SKILLS, saved=False,
                welcome=request.query_params.get("welcome") == "1")


@app.post("/profile")
def profile_save(
    request: Request,
    full_name: str = Form(...),
    skills: str = Form(""),
    bio: str = Form(""),
    preferred_type: str = Form("any"),
    preferred_mode: str = Form("any"),
    min_score: int = Form(50),
    notify: str = Form(""),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    user.full_name = full_name.strip() or user.full_name
    user.skills = clean_skills(skills)
    user.bio = bio.strip()[:1500]
    user.preferred_type = preferred_type if preferred_type in ("any", "Internship", "Job", "Hackathon") else "any"
    user.preferred_mode = preferred_mode if preferred_mode in ("any", "Remote", "Hybrid", "On-site") else "any"
    user.min_score = max(0, min(100, min_score))
    user.notify = notify == "on"
    db.merge(user)
    db.commit()
    return page(request, "profile.html", user, "profile", suggestions=SKILLS, saved=True, welcome=False)


# ---------- Administration ----------
@app.post("/api/admin/scrape")
def admin_scrape(user: User = Depends(admin_user)):
    return run_scrape()


@app.post("/api/admin/demo")
def admin_demo(user: User = Depends(admin_user), db=Depends(get_db)):
    return {"added": load_demo(db)}
