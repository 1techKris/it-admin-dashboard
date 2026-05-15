from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {**data, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)