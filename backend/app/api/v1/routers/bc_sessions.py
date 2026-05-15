from fastapi import APIRouter, HTTPException
from app.services.bc_sessions import get_bc_sessions, kill_bc_session

router = APIRouter(prefix="/bc", tags=["Business Central"])


@router.get("/sessions")
async def list_sessions():
    try:
        return get_bc_sessions()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch BC sessions: {e}",
        )


@router.post("/sessions/{session_id}/kill")
async def kill_session(session_id: int):
    try:
        return kill_bc_session(session_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to kill BC session: {e}",
        )
