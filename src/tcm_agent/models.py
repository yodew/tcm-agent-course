"""Persistence rows. Health payloads are separate from authentication config."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class VisitRow(Base):
    """Mutable ORM record; version increments on every successful state change."""

    __tablename__: str = "visits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(Text)


class OperationRow(Base):
    """Mutable idempotency record with fencing token for crash recovery."""

    __tablename__: str = "operations"
    session_id: Mapped[str] = mapped_column(ForeignKey("visits.id"), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    body_hash: Mapped[str] = mapped_column(String(64))
    request_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))
    lease: Mapped[str] = mapped_column(String(36))
    started: Mapped[int] = mapped_column(Integer)
    response: Mapped[str] = mapped_column(Text, default="")
