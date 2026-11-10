# JobHub — plateforme de veille de stages

Application web qui **scrape périodiquement plusieurs sites d'offres**, **détecte les nouvelles offres**,
calcule un **score de correspondance** avec le profil de chaque utilisateur et **envoie des alertes email**.

## Fonctions
- Création de compte / connexion (mots de passe hachés PBKDF2, sessions signées). Le **1er compte créé est administrateur**.
- **Tableau de bord** : indicateurs, graphiques (offres par jour, type, source, compétences demandées), meilleures correspondances.
- **Recommandations** : liste à gauche, détail à droite, score en % avec compétences acquises / à développer.
- **Toutes les offres** : recherche, filtres (type, mode), pagination, sauvegarde.
- **Assistant carrière** : Claude si `ANTHROPIC_API_KEY` est défini, sinon réponses par règles (fonctionne sans clé).
- **Scraping automatique** (APScheduler, toutes les 6 h par défaut) + bouton manuel pour l'admin.
- **Alertes email** : seulement les nouvelles offres dont le score dépasse le seuil de l'utilisateur.
- Mode sombre, responsive.

## Lancer (Python 3.10+)
**Windows** : double-clique sur `run.bat` (ou lance-le dans PowerShell).
**Mac / Linux** : `./run.sh`

Manuellement :
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux : source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # Mac/Linux : cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```
Ouvre http://localhost:8000, crée un compte (il sera admin), complète ton profil, puis sur le tableau de bord clique sur **Lancer le scraping**.
Au premier lancement, 24 offres de démonstration sont chargées si `USE_DEMO=1` (leurs liens « Postuler » pointent vers example.com).

## Configuration (`.env`)
| Variable | Rôle |
|---|---|
| `SECRET_KEY` | signature des sessions (longue valeur aléatoire) |
| `USE_DEMO` | 1 = charge des offres de démo si la base est vide |
| `SCRAPE_INTERVAL_HOURS` | fréquence du scraping automatique |
| `EMAIL_USER` / `EMAIL_PASS` | SMTP — utilise un **mot de passe d'application** |
| `ANTHROPIC_API_KEY` | active le chatbot Claude (optionnel) |

⚠️ Ne mets jamais de vraies clés dans `.env.example`. Seul `.env` contient les secrets, et il est dans `.gitignore`.

## Structure
```
app/
  main.py         routes FastAPI, pages et API JSON
  models.py       User, Offer (URL unique), SavedOffer
  scrapers.py     sources (Remotive, Arbeitnow, RemoteOK) → ajoute les tiennes dans SOURCES
  service.py      détection des nouvelles offres + orchestration
  recommender.py  score = 50 % compétences + 30 % TF-IDF + 20 % préférences
  chatbot.py      Claude + mode règles
  notifier.py     emails        scheduler.py  planification
  templates/ static/   interface (HTML, CSS, JS, Chart.js)
```

## Ajouter une source de scraping
Dans `scrapers.py`, écris `fetch_ma_source()` qui retourne une liste de `make_offer(...)`, puis ajoute-la à `SOURCES`.
Préfère une API ou un flux RSS plutôt que du HTML (les sites comme LinkedIn ou Indeed bloquent le scraping).

## Dépannage
- Tableau de bord vide : clique sur « Lancer le scraping » (admin) ou « Charger la démo ».
- Une source en échec : le message de fin de scraping indique laquelle ; les autres continuent.
- Pas d'email reçu : vérifie `EMAIL_USER`, le mot de passe d'application et le seuil de score dans ton profil.
