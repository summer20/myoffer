from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, ForeignKey
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


# Stub Application class - placeholder for Task 4
# The full implementation will replace this in Task 4
class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    company = relationship("Company", back_populates="applications")
