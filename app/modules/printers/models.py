from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

# Your existing Printer model should look similar to this:
class Printer(Base):
    __tablename__ = "printers"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    ip_address = Column(String, unique=True, index=True)
    model = Column(String, nullable=True)
    status = Column(Boolean, default=True)  # online/offline
    # created_at = Column(DateTime, default=datetime.utcnow)  # optional

    supplies = relationship("PrinterSupplies", back_populates="printer", cascade="all, delete-orphan", uselist=False)


class PrinterSupplies(Base):
    """
    Optional supplies snapshot. We keep it lean:
    - BK, C, M, Y: toner % (0..100) or None
    """
    __tablename__ = "printer_supplies"

    id = Column(Integer, primary_key=True)
    printer_id = Column(Integer, ForeignKey("printers.id"), unique=True, index=True)

    bk = Column(Integer, nullable=True)
    c = Column(Integer, nullable=True)
    m = Column(Integer, nullable=True)
    y = Column(Integer, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow)

    printer = relationship("Printer", back_populates="supplies")