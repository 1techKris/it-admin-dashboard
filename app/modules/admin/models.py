from sqlalchemy import Column, Integer, String
from app.core.database import Base

class DashboardUser(Base):
    __tablename__ = "dashboard_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)  # bcrypt hashes
    role = Column(String)  # admin, read, helpdesk, etc.