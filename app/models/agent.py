from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.human import Human
    from app.models.verification_log import VerificationLog


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    human_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("humans.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_salt: Mapped[str] = mapped_column(String(255), nullable=False)
    signature: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    signature_vector = mapped_column(Vector(256), nullable=True)
    # RFC 0002: which encoding produced signature_vector. NULL/1 = legacy layout,
    # 2 = hashed-band encoding. Used by the re-embedding backfill to find stale rows.
    signature_version: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    human: Mapped[Human] = relationship("Human", back_populates="agents")
    verification_logs: Mapped[list[VerificationLog]] = relationship(
        "VerificationLog", back_populates="agent"
    )
