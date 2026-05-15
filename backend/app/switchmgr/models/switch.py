from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base

class Switch(Base):
    __tablename__ = "switches"

    id = Column(String, primary_key=True)  # IP or UUID
    ip = Column(String, unique=True, index=True, nullable=False)
    hostname = Column(String)
    vendor = Column(String)
    model = Column(String)
    os_version = Column(String)
    mgmt_protocol = Column(String, default="snmp")  # snmp/ssh/api

    ports = relationship("SwitchPort", back_populates="switch")