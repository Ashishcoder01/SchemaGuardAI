
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class SchemaRecord(Base):
    __tablename__ = "schemas"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(
        String(500), default=""
    )
    version: Mapped[int] = mapped_column(
        Integer, default=1
    )
    schema_json: Mapped[dict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    status: Mapped[str] = mapped_column(
        String(30), default="success"
    )
    model: Mapped[str] = mapped_column(
        String(120), default="mock"
    )
    prompt_preview: Mapped[str] = mapped_column(
        String(500), default=""
    )
    prompt: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(80))
    schema_name: Mapped[str] = mapped_column(
        String(150), default="legacy"
    )
    success: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    attempts: Mapped[int] = mapped_column(
        Integer, default=1
    )
    latency_ms: Mapped[float] = mapped_column(
        Float, default=0.0
    )
    output_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    errors_json: Mapped[list] = mapped_column(
        JSON, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
