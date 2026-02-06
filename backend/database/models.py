"""
SQLAlchemy models for beta: users (doctors), INI uploads, extracted measurements,
predictions, and outcomes. PHI (name, DOB) is not stored; only measurements and Age.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """Beta tester (doctor). Add auth fields (password_hash, etc.) when you add auth."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    uploads = relationship("Upload", back_populates="user", cascade="all, delete-orphan")


class Upload(Base):
    """One row per INI file upload. No PHI stored here."""

    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    # Optional: key into blob storage if you store raw INI (encrypted). Not PHI in DB.
    ini_storage_key = Column(String(512), nullable=True)

    user = relationship("User", back_populates="uploads")
    extracted = relationship(
        "ExtractedMeasurements",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
    )
    prediction = relationship(
        "Prediction",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
    )
    outcome = relationship(
        "Outcome",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ExtractedMeasurements(Base):
    """Parsed values from INI (no name/DOB). Age is stored as numeric only."""

    __tablename__ = "extracted_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(
        Integer,
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Core measurements
    age = Column(Float, nullable=True)
    wtw = Column(Float, nullable=True)
    acd_internal = Column(Float, nullable=True)
    acv = Column(Float, nullable=True)
    ac_shape_ratio = Column(Float, nullable=True)
    simk_steep = Column(Float, nullable=True)
    cct = Column(Float, nullable=True)
    tcrp_km = Column(Float, nullable=True)
    tcrp_astigmatism = Column(Float, nullable=True)
    eye = Column(String(8), nullable=True)
    # Optional: full extracted dict as JSON for flexibility (still no PHI keys)
    extracted_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    upload = relationship("Upload", back_populates="extracted")


class Prediction(Base):
    """Model prediction at upload time (lens size, vault, probabilities)."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(
        Integer,
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    lens_size_mm = Column(Float, nullable=False)
    lens_probability = Column(Float, nullable=False)
    vault_pred_um = Column(Integer, nullable=False)
    vault_range_low_um = Column(Integer, nullable=True)
    vault_range_high_um = Column(Integer, nullable=True)
    vault_flag = Column(String(16), nullable=True)  # low | ok | high
    size_probabilities_json = Column(JSONB, nullable=True)  # list of {size_mm, probability}
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    upload = relationship("Upload", back_populates="prediction")


class Outcome(Base):
    """Expected/actual result: vault and lens size (entered by doctor after surgery/follow-up)."""

    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(
        Integer,
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    actual_vault_um = Column(Integer, nullable=True)
    actual_lens_size_mm = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    upload = relationship("Upload", back_populates="outcome")
