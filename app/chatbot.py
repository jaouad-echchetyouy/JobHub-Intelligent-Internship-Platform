import logging
from collections import Counter

from . import config

log = logging.getLogger(__name__)


def _context(user, ranked) -> str:
    lines = [
        f"- {r['offer'].title} @ {r['offer'].company} ({r['offer'].job_type}, {r['offer'].work_mode}) "
        f"score {r['score']}% ; compétences à acquérir : {', '.join(r['missing'][:4]) or 'aucune'}"
        for r in ranked[:12]
    ]
    return (
        "Tu es un conseiller de carrière bienveillant et concret pour un étudiant. Réponds en français, "
        "en 150 mots maximum, avec des listes courtes quand c'est utile.\n"
        f"Profil : compétences = {', '.join(user.skill_list) or 'non renseignées'} ; bio = {user.bio or 'vide'}.\n"
        "Meilleures offres actuelles :\n" + "\n".join(lines)
    )


def _claude(question, user, ranked, history) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msgs = [m for m in (history or []) if m.get("role") in ("user", "assistant") and m.get("content")][-8:]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    clean, last = [], None
    for m in msgs:
        if m["role"] != last:
            clean.append({"role": m["role"], "content": str(m["content"])[:2000]})
            last = m["role"]
    if clean and clean[-1]["role"] == "user":
        clean.pop()
    clean.append({"role": "user", "content": question})
    r = client.messages.create(model=config.CLAUDE_MODEL, max_tokens=600, system=_context(user, ranked), messages=clean)
    return r.content[0].text


def _top_list(ranked, n=5) -> str:
    return "\n".join(
        f"- **{r['offer'].title}** — {r['offer'].company or 'Entreprise'} ({r['score']} %)" for r in ranked[:n]
    )


def _rules(question, user, ranked) -> str:
    q = question.lower()
    if not ranked:
        return "Je n'ai pas encore d'offres à analyser. Demande à un administrateur de lancer le scraping depuis le tableau de bord."
    if any(w in q for w in ("bonjour", "salut", "hello", "bonsoir", "hi")):
        return f"Bonjour {user.first_name} ! Je peux te proposer des offres adaptées, te dire quelles compétences travailler ou t'aider pour ta candidature. Que veux-tu faire ?"
    if any(w in q for w in ("compétence", "competence", "skill", "améliorer", "ameliorer", "apprendre", "manque")):
        missing = Counter(s for r in ranked[:10] for s in r["missing"]).most_common(5)
        if not missing:
            return "Ton profil couvre déjà bien les meilleures offres. Continue à enrichir ta bio avec des projets concrets."
        items = "\n".join(f"- **{s}** (demandé dans {c} offres)" for s, c in missing)
        return f"Pour augmenter tes scores, travaille en priorité ces compétences :\n{items}"
    if any(w in q for w in ("remote", "télétravail", "teletravail", "distance")):
        remote = [r for r in ranked if r["offer"].work_mode == "Remote"]
        return "Meilleures offres en remote :\n" + _top_list(remote) if remote else "Aucune offre remote pour le moment."
    if any(w in q for w in ("cv", "lettre", "candidature", "postuler", "entretien")):
        return (
            "Conseils pour candidater :\n- Adapte ton CV : mets en avant les compétences citées dans l'offre.\n"
            "- Ajoute 2 projets concrets avec un lien GitHub.\n- Rédige une lettre courte (8 lignes) centrée sur ce que tu apportes.\n"
            "- Prépare 3 exemples pour l'entretien (problème, action, résultat)."
        )
    if any(w in q for w in ("offre", "stage", "internship", "job", "recommand", "meilleur", "propose")):
        return "Voici les offres qui correspondent le mieux à ton profil :\n" + _top_list(ranked)
    return (
        "Je peux t'aider sur trois sujets :\n- **Offres** : « quelles offres me conviennent ? »\n"
        "- **Compétences** : « quelles compétences améliorer ? »\n- **Candidature** : « comment améliorer mon CV ? »"
    )


def reply(question: str, user, ranked, history=None) -> dict:
    if config.ANTHROPIC_API_KEY:
        try:
            return {"answer": _claude(question, user, ranked, history), "mode": "claude"}
        except Exception as exc:
            log.warning("Claude indisponible, bascule en mode règles : %s", exc)
    return {"answer": _rules(question, user, ranked), "mode": "rules"}
