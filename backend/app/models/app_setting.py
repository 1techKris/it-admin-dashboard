from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text
from app.models.base import Base

class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text)