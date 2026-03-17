from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from datetime import datetime

from app.models.base import Base

class Printer(Base):
    __tablename__ = "printers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128))                 # display/custom name
    ip: Mapped[str] = mapped_column(String(64), unique=True)       # IP address
    status: Mapped[str] = mapped_column(String(32), default="Unknown")  # Healthy | Warning | Down | Unknown
    vendor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial: Mapped[str | None] = mapped_column(String(128), nullable=True)

    supplies_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string of supplies snapshot
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    archived: Mapped[bool] = mapped_column(Boolean, default=False)