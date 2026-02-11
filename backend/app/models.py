"""
SQLAlchemy ORM models for Job and Candidate.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, Text, DateTime,
)
from sqlalchemy.orm import relationship
from .database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="processing", index=True)
    total_files = Column(Integer, nullable=False)
    processed_files = Column(Integer, default=0)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    candidates = relationship("Candidate", back_populates="job", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, status={self.status}, "
            f"processed={self.processed_files}/{self.total_files})>"
        )


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    name = Column(String, default="Unknown")
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    github = Column(String, nullable=True)
    score = Column(Float, default=0.0)
    classification = Column(String, default="Partial")
    summary = Column(Text, default="")

    job = relationship("Job", back_populates="candidates")

    def __repr__(self) -> str:
        return (
            f"<Candidate(id={self.id}, name={self.name}, "
            f"score={self.score}, classification={self.classification})>"
        )
