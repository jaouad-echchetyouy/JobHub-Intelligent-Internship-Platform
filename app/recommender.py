"""Score de recommandation (0-100) sans dépendance lourde.

score = 50 % compétences + 30 % similarité texte (TF-IDF) + 20 % préférences
"""
import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-zà-ÿ0-9+#.]{2,}")
_STOP = set(
    "the and for with you your are our will from that this have has not but all can any "
    "des les une pour avec dans sur par que qui est sont aux vous nous notre votre ou et "
    "de du la le un en au ce se sa son ses a an of to in on at as be is or".split()
)


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall((text or "").lower()) if t not in _STOP]


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    return {t: c * idf.get(t, 1.0) for t, c in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def score_offers(user, offers) -> list[dict]:
    offers = list(offers)
    if not offers:
        return []

    docs = [_tokens(f"{o.title} {o.title} {o.skills} {o.description}") for o in offers]
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(set(d))
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}

    user_skills = set(user.skill_list)
    profile_text = " ".join(user.skill_list) * 2 + " " + (user.bio or "")
    profile_vec = _vector(_tokens(profile_text), idf)

    results = []
    for o, d in zip(offers, docs):
        o_skills = set(o.skill_list)
        matching = sorted(user_skills & o_skills)
        missing = sorted(o_skills - user_skills)

        if o_skills:
            skills_score = len(matching) / len(o_skills)
        else:
            skills_score = 0.3 if user_skills else 0.0

        text_score = min(1.0, _cosine(profile_vec, _vector(d, idf)) * 3)

        type_ok = 1.0 if user.preferred_type in ("any", None, o.job_type) else 0.3
        mode_ok = 1.0 if user.preferred_mode in ("any", None, o.work_mode) else 0.4
        pref_score = (type_ok + mode_ok) / 2

        overall = round(100 * (0.5 * skills_score + 0.3 * text_score + 0.2 * pref_score))
        results.append(
            {
                "offer": o,
                "score": overall,
                "skills_pct": round(skills_score * 100),
                "text_pct": round(text_score * 100),
                "pref_pct": round(pref_score * 100),
                "matching": matching,
                "missing": missing,
            }
        )

    results.sort(key=lambda r: (r["score"], r["offer"].created_at.timestamp() if r["offer"].created_at else 0), reverse=True)
    return results
