from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def utcnow() -> datetime:
    """Naive UTC (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Vendor(Base):
    __tablename__ = "vendors"
    vendor_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    account_number: Mapped[str] = mapped_column(String)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)


class Invoice(Base):
    __tablename__ = "invoices"
    invoice_id: Mapped[str] = mapped_column(String, primary_key=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.vendor_id"))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="INR")
    due_date: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    raw_text: Mapped[str] = mapped_column(String)


class Transaction(Base):
    __tablename__ = "transactions"
    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    vendor_id: Mapped[str] = mapped_column(String)
    account_number: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    invoice_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    agent: Mapped[str] = mapped_column(String, default="system")  # baseline | camel
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
