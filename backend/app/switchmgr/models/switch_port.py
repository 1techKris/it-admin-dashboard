from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class SwitchPort(Base):
    __tablename__ = "switch_ports"

    id = Column(String, primary_key=True)          # e.g. "10.0.0.5:1"
    switch_id = Column(String, ForeignKey("switches.id"))
    port_number = Column(Integer)
    name = Column(String)
    vlan = Column(Integer)
    enabled = Column(Boolean)
    poe = Column(Boolean)
    speed = Column(String)
    duplex = Column(String)
    macs = Column(String)  # JSON-encoded list

    switch = relationship("Switch", back_populates="ports")