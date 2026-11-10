from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def split_csv(value: str | None) -> list[str]:
    return [s.strip().lower() for s in (value or "").split(",") if s.strip()]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    skills = Column(Text, default="")
    bio = Column(Text, default="")
    preferred_type = Column(String(20), default="any")   # any / Internship / Job / Hackathon
    preferred_mode = Column(String(20), default="any")   # any / Remote / Hybrid / On-site
    min_score = Column(Integer, default=50)
    notify = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    @property
    def skill_list(self) -> list[str]:
        return split_csv(self.skills)

    @property
    def first_name(self) -> str:
        return (self.full_name or "").split(" ")[0] or "toi"

    @property
    def initials(self) -> str:
        parts = (self.full_name or "?").split()
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def profile_completeness(self) -> int:
        pts = 0
        pts += 30 if self.skill_list else 0
        pts += 20 if len(self.skill_list) >= 4 else 0
        pts += 30 if (self.bio or "").strip() else 0
        pts += 10 if self.preferred_type != "any" else 0
        pts += 10 if self.preferred_mode != "any" else 0
        return pts


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    company = Column(String(200), default="")
    location = Column(String(200), default="")
    work_mode = Column(String(20), default="On-site")    # Remote / Hybrid / On-site
    job_type = Column(String(20), default="Job")         # Internship / Job / Hackathon
    description = Column(Text, default="")
    skills = Column(Text, default="")
    url = Column(String(700), unique=True, nullable=False, index=True)  # UNIQUE = détection des nouveautés
    source = Column(String(60), default="")
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)

    @property
    def skill_list(self) -> list[str]:
        return split_csv(self.skills)


class SavedOffer(Base):
    __tablename__ = "saved_offers"
    __table_args__ = (UniqueConstraint("user_id", "offer_id", name="uq_user_offer"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    offer_id = Column(Integer, ForeignKey("offers.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=utcnow)
