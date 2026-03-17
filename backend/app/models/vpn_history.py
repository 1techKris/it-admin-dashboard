# backend/app/models/vpn_history.py

from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class VPNHistory(Base):
    __tablename__ = "vpn_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    username = Column(String(200), index=True)
    ipv4 = Column(String(100))
    connected_from = Column(String(200))  # TunnelEndpoint or CallingStationID
    geo_country = Column(String(100))
    geo_city = Column(String(100))
    geo_isp = Column(String(200))
    geo_org = Column(String(200))

    start_time = Column(DateTime)          # When connection started
    end_time = Column(DateTime)            # When disconnected
    duration_seconds = Column(Integer)     # numeric duration
    timestamp_logged = Column(DateTime, default=datetime.utcnow)

    raw_json = Column(Text)                # full raw session JSON for auditing