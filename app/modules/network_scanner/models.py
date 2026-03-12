from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from app.core.database import Base

class ScannedHost(Base):
    __tablename__ = "scanned_hosts"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, index=True)
    hostname = Column(String, nullable=True)
    vendor = Column(String, nullable=True)        # MAC vendor (if available)
    os_guess = Column(String, nullable=True)      # crude OS guess (ports/DNS)
    open_ports = Column(String, nullable=True)    # CSV list of ports
    last_seen = Column(DateTime, default=datetime.utcnow)
    monitored = Column(Boolean, default=False)
    host_type = Column(String, default="unknown") # server | printer | network | unknown

class SubnetProfile(Base):
    __tablename__ = "subnet_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)            # e.g., "Office LAN"
    cidr = Column(String)                         # e.g., "192.168.125.0/24"
    notes = Column(Text, nullable=True)
    last_used = Column(DateTime, nullable=True)