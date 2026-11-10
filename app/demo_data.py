import random
from datetime import timedelta

from .models import Offer, utcnow

# (titre, entreprise, lieu, mode, type, compétences, description, source)
DEMO = [
    ("Stage Développeur Full Stack", "Atlas Digital", "Casablanca, Maroc", "Hybrid", "Internship",
     "react,node.js,mongodb,typescript", "Participez à la création d'une plateforme web moderne avec une équipe agile. Vous développerez des interfaces React et des API Node.js.", "Demo"),
    ("Data Analyst Intern", "Nimbus Analytics", "Rabat, Maroc", "On-site", "Internship",
     "sql,python,excel,power bi", "Analysez de grands jeux de données pour produire des tableaux de bord utiles aux équipes métier. Python, SQL et Power BI au quotidien.", "Demo"),
    ("Machine Learning Intern", "Kasbah AI", "Remote", "Remote", "Internship",
     "python,machine learning,pandas,scikit-learn", "Entraînez et évaluez des modèles de classification de texte. Vous travaillerez avec pandas et scikit-learn sur des données réelles.", "Demo"),
    ("Stage DevOps Junior", "Sahara Cloud", "Fès, Maroc", "On-site", "Internship",
     "docker,linux,git,ci/cd", "Automatisez les déploiements, surveillez les services et apprenez les bonnes pratiques CI/CD dans une équipe cloud.", "Demo"),
    ("UI/UX Design Intern", "Zellige Studio", "Remote", "Remote", "Internship",
     "figma,ui/ux,communication", "Concevez des maquettes et des prototypes pour des applications mobiles. Recherche utilisateur et tests inclus.", "Demo"),
    ("Backend Developer Intern", "Medina Pay", "Casablanca, Maroc", "Hybrid", "Internship",
     "java,spring,mysql,rest api", "Construisez les services d'une infrastructure de paiement : API REST sécurisées, base MySQL, tests automatisés.", "Demo"),
    ("Junior Python Developer", "Oasis Software", "Remote", "Remote", "Job",
     "python,django,postgresql,git", "Rejoignez une équipe produit pour développer des fonctionnalités Django, écrire des tests et améliorer les performances.", "Demo"),
    ("AI Hackathon 2026", "Maghreb Tech Community", "Marrakech, Maroc", "On-site", "Hackathon",
     "python,machine learning,nlp", "48 heures pour construire une solution d'IA à impact social. Mentors, prix et opportunités de stage à la clé.", "Demo"),
    ("Cybersecurity Intern", "Fortress Secure", "Rabat, Maroc", "On-site", "Internship",
     "cybersecurity,linux,networking,python", "Participez à des audits de sécurité, analysez des vulnérabilités et rédigez des rapports pour des clients.", "Demo"),
    ("Mobile Developer Intern (Flutter)", "Dar Apps", "Remote", "Remote", "Internship",
     "flutter,git,rest api", "Développez une application mobile multiplateforme avec Flutter et intégrez des API REST.", "Demo"),
    ("Stage Business Intelligence", "Argan Retail", "Tanger, Maroc", "Hybrid", "Internship",
     "sql,power bi,excel,data analysis", "Construisez des rapports Power BI pour le suivi des ventes et automatisez la collecte de données.", "Demo"),
    ("Frontend Developer Intern", "Pixel Souk", "Fès, Maroc", "Hybrid", "Internship",
     "javascript,react,html,css", "Créez des interfaces responsives et accessibles pour une marketplace. Collaboration étroite avec les designers.", "Demo"),
    ("Data Engineer Intern", "Delta Data", "Remote", "Remote", "Internship",
     "python,sql,docker,aws", "Aidez à construire des pipelines de données fiables : ingestion, nettoyage, orchestration et supervision.", "Demo"),
    ("Hackathon Smart City", "Ministère de la Transition Numérique", "Casablanca, Maroc", "On-site", "Hackathon",
     "problem solving,python,javascript", "36 heures pour imaginer des services numériques pour la ville de demain. Finale devant un jury d'experts.", "Demo"),
    ("Software Engineer Intern", "Helix Systems", "Remote", "Remote", "Internship",
     "python,java,git,agile", "Contribuez à un produit SaaS : corrections, nouvelles fonctionnalités et revues de code avec des ingénieurs seniors.", "Demo"),
    ("Stage Marketing Digital & SEO", "Nomad Media", "Rabat, Maroc", "Hybrid", "Internship",
     "marketing,seo,communication,excel", "Optimisez le référencement, analysez les campagnes et produisez des rapports de performance.", "Demo"),
    ("Full Stack Developer", "Cedar Labs", "Remote", "Remote", "Job",
     "react,node.js,postgresql,docker", "Développez des fonctionnalités de bout en bout sur un produit B2B. Poste en télétravail complet.", "Demo"),
    ("QA Automation Intern", "Testify", "Casablanca, Maroc", "On-site", "Internship",
     "selenium,python,git,agile", "Écrivez des tests automatisés Selenium et participez à l'amélioration de la qualité logicielle.", "Demo"),
    ("Cloud Engineer Intern", "Skyline Hosting", "Remote", "Remote", "Internship",
     "aws,linux,docker,kubernetes", "Découvrez l'infrastructure cloud : conteneurs, supervision et déploiements automatisés sur AWS.", "Demo"),
    ("NLP Research Intern", "Lexi Labs", "Remote", "Remote", "Internship",
     "python,nlp,pytorch,deep learning", "Travaillez sur le traitement du texte en arabe et en français avec PyTorch. Publication possible.", "Demo"),
    ("Stage Développeur PHP/Laravel", "Webmaker Maroc", "Fès, Maroc", "On-site", "Internship",
     "php,laravel,mysql,html", "Développez des sites et applications métier avec Laravel et MySQL au sein d'une petite équipe.", "Demo"),
    ("Product Analyst Intern", "Bloom Apps", "Remote", "Remote", "Internship",
     "sql,data analysis,communication,excel", "Suivez les indicateurs produit, lancez des analyses et aidez l'équipe à prioriser les fonctionnalités.", "Demo"),
    ("Hackathon Open Source Africa", "Code for Africa", "Remote", "Remote", "Hackathon",
     "git,python,javascript", "Un week-end pour contribuer à des projets open source qui servent des communautés locales.", "Demo"),
    ("Junior Web Scraping Engineer", "DataHarvest", "Remote", "Remote", "Job",
     "python,scraping,sql,docker", "Concevez des collecteurs de données robustes, gérez les erreurs et planifiez les exécutions.", "Demo"),
]


def load_demo(db) -> int:
    random.seed(7)
    now = utcnow()
    count = 0
    for i, (title, company, location, mode, jtype, skills, desc, source) in enumerate(DEMO, start=1):
        url = f"https://example.com/demo-offer/{i}"
        if db.query(Offer.id).filter_by(url=url).first():
            continue
        created = now - timedelta(days=random.randint(0, 12), hours=random.randint(0, 23))
        db.add(
            Offer(
                title=title, company=company, location=location, work_mode=mode, job_type=jtype,
                description=desc, skills=skills, url=url, source=source,
                posted_at=created, created_at=created,
            )
        )
        count += 1
    db.commit()
    return count
