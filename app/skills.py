import re

SKILLS = [
    "python", "java", "javascript", "typescript", "react", "vue", "angular", "node.js", "html", "css",
    "sql", "mysql", "postgresql", "mongodb", "sqlite", "docker", "kubernetes", "git", "linux", "aws",
    "azure", "gcp", "django", "flask", "fastapi", "spring", "php", "laravel", "c++", "c#", ".net",
    "go", "rust", "kotlin", "swift", "flutter", "machine learning", "deep learning", "nlp", "pandas",
    "numpy", "tensorflow", "pytorch", "scikit-learn", "power bi", "tableau", "excel", "data analysis",
    "statistics", "figma", "ui/ux", "devops", "ci/cd", "rest api", "graphql", "cybersecurity",
    "networking", "scrum", "agile", "communication", "marketing", "seo", "r", "selenium", "scraping",
]

_PATTERNS = {
    s: re.compile(r"(?<![a-z0-9+#.])" + re.escape(s) + r"(?![a-z0-9+#])", re.IGNORECASE) for s in SKILLS
}


def extract_skills(text: str) -> list[str]:
    found = []
    for skill, pat in _PATTERNS.items():
        if skill == "r":
            # "R" seul est trop ambigu : on exige "R language" / "R programming"
            if re.search(r"\bR (language|programming|studio)\b", text or ""):
                found.append(skill)
        elif skill == "go":
            if re.search(r"\b(Golang|Go (language|developer|programming))\b", text or ""):
                found.append(skill)
        elif pat.search(text or ""):
            found.append(skill)
    return found
