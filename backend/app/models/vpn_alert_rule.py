# backend/app/models/vpn_alert_rule.py

from sqlalchemy import Column, Integer, String, Boolean
from app.models.base import Base   # <<< MUST be unified Base

class VPNAlertRule(Base):
    __tablename__ = "vpn_alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(200), unique=True, index=True)
    enabled = Column(Boolean, default=True)