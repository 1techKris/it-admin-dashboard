from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime
from datetime import datetime
from app.models.base import Base

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(32))
    os: Mapped[str] = mapped_column(String(64))
    ip: Mapped[str] = mapped_column(String(64))
    cpu: Mapped[int] = mapped_column(Integer)
    mem: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_name: Mapped[str | None] = mapped_column(String(128), nullable=True)