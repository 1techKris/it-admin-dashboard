from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    UniqueConstraint,
    Text
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


# ==========================================================
# MAIN SERVER TABLE
# ==========================================================
class Server(Base):
    __tablename__ = 'servers'

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String)
    ip_address = Column(String, index=True)
    online = Column(Boolean, default=False)
    last_seen = Column(DateTime)
    wmi_json = Column(Text, nullable=True)


    # Relationships
    status_history = relationship(
        "ServerStatusHistory",
        back_populates="server",
        cascade="all, delete-orphan"
    )
    metrics = relationship(
        "ServerMetrics",
        back_populates="server",
        cascade="all, delete-orphan"
    )


# ==========================================================
# STATUS HISTORY (ping checks)
# ==========================================================
class ServerStatusHistory(Base):
    __tablename__ = "server_status_history"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id"), index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    online = Column(Boolean, default=False)
    ping_ms = Column(Float, nullable=True)

    server = relationship("Server", back_populates="status_history")


# ==========================================================
# METRICS TABLE (CPU / RAM / DISK)
# ==========================================================
class ServerMetrics(Base):
    __tablename__ = "server_metrics"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id"), index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    cpu_percent = Column(Float, nullable=True)
    ram_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)

    server = relationship("Server", back_populates="metrics")


# ==========================================================
# SERVER CREDENTIALS (Windows / Linux)
# ==========================================================
class ServerCredentials(Base):
    __tablename__ = "server_credentials"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id"), unique=True, index=True)

    os_type = Column(String, default="windows")  # windows | linux
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    port = Column(Integer, nullable=True)

    server = relationship("Server")


# ==========================================================
# GROUPS (Prod / Lab / DC / etc)
# ==========================================================
class ServerGroup(Base):
    __tablename__ = "server_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    notes = Column(String, nullable=True)

    members = relationship(
        "ServerGroupMember",
        back_populates="group",
        cascade="all, delete-orphan"
    )


class ServerGroupMember(Base):
    __tablename__ = "server_group_members"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id"), index=True)
    group_id = Column(Integer, ForeignKey("server_groups.id"), index=True)

    server = relationship("Server")
    group = relationship("ServerGroup", back_populates="members")

    __table_args__ = (
        UniqueConstraint("server_id", "group_id", name="uq_server_group_member"),
    )


# ==========================================================
# TAGS (any custom labels)
# ==========================================================
class ServerTag(Base):
    __tablename__ = "server_tags"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id"), index=True)
    tag = Column(String, index=True)

    server = relationship("Server")
    
# ----------------------------------------------------------
# Global Settings (Key/Value store)
# ----------------------------------------------------------
from sqlalchemy import Column, Integer, String

class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(String(500))


# ----------------------------------------------------------
# Helper functions (must be at root indentation level!)
# ----------------------------------------------------------
def get_setting(db, key: str):
    row = db.query(GlobalSettings).filter(GlobalSettings.key == key).first()
    return row.value if row else None


def set_setting(db, key: str, value: str):
    row = db.query(GlobalSettings).filter(GlobalSettings.key == key).first()
    if not row:
        row = GlobalSettings(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()