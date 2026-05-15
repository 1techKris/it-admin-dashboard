from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ldap_auth import authenticate_ldap_user
from app.services.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    try:
        user = authenticate_ldap_user(req.username, req.password)
        token = create_access_token(user)
        return {"access_token": token}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")