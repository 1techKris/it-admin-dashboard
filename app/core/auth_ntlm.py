from fastapi import Request, HTTPException

async def ntlm_auth(request: Request):
    """
    Placeholder NTLM authentication.

    When running behind IIS or NGINX configured with NTLM:
    - IIS sets request.headers['X-Remote-User']
    - We read that here
    """
    user = request.headers.get("X-Remote-User")

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user