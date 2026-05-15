from sqlalchemy import Column, String, Integer, DateTime, Float
from sqlalchemy.sql import func
from app.models.base import Base


class ScanHistory(Base):
    __tablename__ = "scan_history"

    # UUID string for scan_id
    id = Column(String, primary_key=True, index=True)

    # CIDR used for the scan
    cidr = Column(String, nullable=False)

    # Number of hosts total / completed
    total = Column(Integer, nullable=False)
    completed = Column(Integer, nullable=False)

    # running / finished / cancelled / error
    status = Column(String, nullable=False)

    # When scan began
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # When scan finished (nullable while running)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Speed profile used
    speed_concurrency = Column(Integer, nullable=False)
    speed_delay = Column(Float, nullable=False)