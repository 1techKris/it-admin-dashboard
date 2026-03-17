# backend/app/services/vpn_alert_rules_init.py

from app.models.vpn_alert_rule import VPNAlertRule
from app.db.session import engine
from sqlalchemy.orm import declarative_base

def init_alert_rules_db():
    from app.models.vpn_alert_rule import Base
    Base.metadata.create_all(bind=engine)