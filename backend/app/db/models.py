"""SQLAlchemy ORM models for transit network, schedules, fares, and user data."""

from datetime import UTC, date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# ==============================================================================
# AUTH & USER DOMAIN
# ==============================================================================

class User(Base, TimestampMixin):
    """User account entity."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    saved_trips: Mapped[list["SavedTrip"]] = relationship(
        "SavedTrip", back_populates="user", cascade="all, delete-orphan"
    )
    places: Mapped[list["UserPlace"]] = relationship(
        "UserPlace", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Rotating refresh token with revocation tracking."""
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(Base):
    """Single-use password reset token."""
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class EmailVerificationToken(Base):
    """Email verification token."""
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class UserPlace(Base, TimestampMixin):
    """Personal saved places (e.g. Home, College)."""
    __tablename__ = "user_places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)  # "Home", "College"
    place_id: Mapped[str] = mapped_column(String(100), nullable=False)  # Station code or city ID
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="places")


class SavedTrip(Base, TimestampMixin):
    """Saved multi-leg itineraries."""
    __tablename__ = "saved_trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    intent_json: Mapped[str] = mapped_column(Text, nullable=False)
    itinerary_json: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="saved_trips")


class SearchHistory(Base):
    """Audit log of user searches."""
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    parsed_intent_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# ==============================================================================
# GEOGRAPHY & TRANSIT NETWORK DOMAIN
# ==============================================================================

class City(Base):
    """Indian city or regional administrative node."""
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)

    stations: Mapped[list["Station"]] = relationship("Station", back_populates="city")


class Station(Base):
    """Transit node: Railway station, bus stand/terminal, or airport."""
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # BZA, DMM, etc.
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # "rail", "bus_stand", "airport"
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"), index=True, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)

    city: Mapped[Optional["City"]] = relationship("City", back_populates="stations")
    stop_times: Mapped[list["StopTime"]] = relationship("StopTime", back_populates="station")


class Alias(Base):
    """Alternate names, local phonetic spellings, and Telugu/Hindi translations."""
    __tablename__ = "aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    station_id: Mapped[int | None] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), nullable=True, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), nullable=True, index=True)
    lang: Mapped[str] = mapped_column(String(10), default="en", nullable=False)  # "en", "te", "hi"

    __table_args__ = (
        Index("ix_aliases_alias_lang", "alias", "lang"),
    )


class Service(Base):
    """Scheduled transit service (e.g. 12785 KCG-MYS Express, APSRTC Amaravathi Bus)."""
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Unique service identifier
    mode: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # "rail", "bus", "flight"
    operator: Mapped[str] = mapped_column(String(100), nullable=False)  # "Indian Railways", "APSRTC", "IndiGo"
    number: Mapped[str] = mapped_column(String(30), index=True, nullable=False)  # "12785", "6201"
    name: Mapped[str] = mapped_column(String(150), nullable=False)  # "Kacheguda Express"
    source_id: Mapped[str] = mapped_column(String(50), nullable=False)  # ID in data_sources
    truth_level: Mapped[str] = mapped_column(String(30), nullable=False)  # "OFFICIAL_TIMETABLE", "COMMUNITY_GTFS"

    stop_times: Mapped[list["StopTime"]] = relationship(
        "StopTime", back_populates="service", cascade="all, delete-orphan", order_by="StopTime.seq"
    )
    calendar: Mapped[Optional["Calendar"]] = relationship(
        "Calendar", back_populates="service", uselist=False, cascade="all, delete-orphan"
    )
    calendar_exceptions: Mapped[list["CalendarException"]] = relationship(
        "CalendarException", back_populates="service", cascade="all, delete-orphan"
    )
    fares: Mapped[list["Fare"]] = relationship(
        "Fare", back_populates="service", cascade="all, delete-orphan"
    )


class StopTime(Base):
    """Individual stop within a scheduled transit service."""
    __tablename__ = "stop_times"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True, nullable=False)
    arrive: Mapped[str] = mapped_column(String(8), nullable=False)  # "HH:MM:SS"
    depart: Mapped[str] = mapped_column(String(8), nullable=False)  # "HH:MM:SS"
    day_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=same day, 1=next day
    seq: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3...

    service: Mapped["Service"] = relationship("Service", back_populates="stop_times")
    station: Mapped["Station"] = relationship("Station", back_populates="stop_times")

    __table_args__ = (
        Index("ix_stop_times_station_depart", "station_id", "depart"),
        Index("ix_stop_times_service_seq", "service_id", "seq"),
    )


class Calendar(Base):
    """Weekly recurrence pattern for a service."""
    __tablename__ = "calendars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Bitmask for Monday (1) to Sunday (64); All days = 127
    run_days: Mapped[int] = mapped_column(Integer, default=127, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)

    service: Mapped["Service"] = relationship("Service", back_populates="calendar")


class CalendarException(Base):
    """Specific dates when service is added or cancelled."""
    __tablename__ = "calendar_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    exception_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Service added, 2=Service cancelled

    service: Mapped["Service"] = relationship("Service", back_populates="calendar_exceptions")

    __table_args__ = (
        Index("ix_calendar_exceptions_service_date", "service_id", "exception_date"),
    )


class Fare(Base):
    """Station-to-station tariff record."""
    __tablename__ = "fares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False)
    from_station_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    to_station_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    class_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # "SL", "3A", "2A", "CC", "EXP"
    amount_inr: Mapped[float | None] = mapped_column(Float, nullable=True)  # NULLABLE for honest unknown pricing
    truth_level: Mapped[str] = mapped_column(String(30), nullable=False)  # "OFFICIAL_TIMETABLE", "ESTIMATED", "UNKNOWN"

    service: Mapped["Service"] = relationship("Service", back_populates="fares")

    __table_args__ = (
        Index("ix_fares_from_to_class", "from_station_code", "to_station_code", "class_code"),
    )


class AvailabilitySnapshot(Base):
    """Point-in-time seat availability snapshot."""
    __tablename__ = "availability_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    class_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "CNF", "RAC", "WL", "UNKNOWN"
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g. 12 for WL 12
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    truth_level: Mapped[str] = mapped_column(String(30), nullable=False)

    __table_args__ = (
        Index("ix_avail_service_date_class", "service_id", "travel_date", "class_code"),
    )


class TransferEdge(Base):
    """Walk or local transfer connection between stations/hubs."""
    __tablename__ = "transfer_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_station_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    to_station_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)  # Transfer time
    cost_inr: Mapped[float | None] = mapped_column(Float, nullable=True)  # Auto-rickshaw / metro fare if known
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_transfer_edges_endpoints", "from_station_code", "to_station_code"),
    )


class DataSource(Base):
    """Registry of transit feeds, licenses, validity windows, and integrity hashes."""
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. "gtfs_rail"
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
