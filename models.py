import datetime as dt
import os
from sqlalchemy import String, Integer, Float, Boolean, JSON, DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

URL = os.getenv("DATABASE_URL", "sqlite:///./sagar.db")
engine = create_engine(URL, connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    pw_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="tourist")  # tourist | provider | admin
    provider_name: Mapped[str | None] = mapped_column(String, nullable=True)

class Listing(Base):  # hotels, ship info, experiences
    __tablename__ = "listings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dest: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)  # Hotel | Ship | Exp
    name: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)  # night | person
    provider: Mapped[str] = mapped_column(String)
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=False)
    start: Mapped[float | None] = mapped_column(Float, nullable=True)
    end: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_verification: Mapped[bool] = mapped_column(Boolean, default=False)  # operator authorization
    verified: Mapped[bool] = mapped_column(Boolean, default=True)

class Rental(Base):
    __tablename__ = "rentals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dest: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    rates: Mapped[dict] = mapped_column(JSON)  # {"h":..,"half":..,"d":..}
    deposit: Mapped[float] = mapped_column(Float)
    licence: Mapped[bool] = mapped_column(Boolean)
    helmet: Mapped[bool] = mapped_column(Boolean)
    min_age: Mapped[int] = mapped_column(Integer)
    mileage: Mapped[float] = mapped_column(Float)  # km per litre, 0 = non-motorized
    route_id: Mapped[str] = mapped_column(String)
    needs_verification: Mapped[bool] = mapped_column(Boolean, default=False)  # e.g. Sajek self-riding rule
    verified: Mapped[bool] = mapped_column(Boolean, default=True)

class Route(Base):
    __tablename__ = "routes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dest: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    distance_km: Mapped[float] = mapped_column(Float)
    speed_kmh: Mapped[float] = mapped_column(Float)
    breaks: Mapped[int] = mapped_column(Integer)
    terrain: Mapped[str] = mapped_column(String)

class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    dest: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # closed_months | day_only_months | warn | warn_months
    months: Mapped[list] = mapped_column(JSON, default=list)
    text: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    effective: Mapped[str] = mapped_column(String)
    last_verified: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Advisory(Base):
    __tablename__ = "advisories"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dest: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    date: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    blocks_all: Mapped[bool] = mapped_column(Boolean, default=True)
    blocks: Mapped[list] = mapped_column(JSON, default=list)

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[float] = mapped_column(Float)

class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String, index=True)
    items: Mapped[list] = mapped_column(JSON)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="Pending")  # Pending | Accepted | Declined
    paid: Mapped[bool] = mapped_column(Boolean, default=False)  # sandbox only
    idem_key: Mapped[str] = mapped_column(String, index=True)

class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)

class Doc(Base):  # RAG knowledge base
    __tablename__ = "docs"
    id: Mapped[int] = mapped_column(primary_key=True)
    en: Mapped[str] = mapped_column(String)
    bn: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    last_verified: Mapped[str] = mapped_column(String)
