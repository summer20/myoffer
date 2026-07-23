from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    JSON,
    DateTime,
    Date,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    industry = Column(String, nullable=False)
    scale_tags = Column(JSON, nullable=False, default=list)
    recruiting_open = Column(Boolean, nullable=False, default=False)
    recruiting_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    applications = relationship(
        "Application", back_populates="company", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    position = Column(String, nullable=False)
    base_city = Column(String, nullable=False)
    stage = Column(String, nullable=False, default="已投递")
    applied_date = Column(Date, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    notes = Column(Text, nullable=True)

    company = relationship("Company", back_populates="applications")


class ResumeModule(Base):
    __tablename__ = "resume_modules"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
