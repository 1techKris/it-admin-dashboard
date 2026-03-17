from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:////home/administrator/it-admin-dashboard/backend/vpn_history.sqlite3"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)