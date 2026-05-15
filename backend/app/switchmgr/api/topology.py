from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.switchmgr.services.topology_service import build_topology

router = APIRouter(prefix="/topology", tags=["topology"])


class TopologyRequest(BaseModel):
    switches: List[str]
    community: str = "public"


@router.post("/", summary="Build raw topology")
async def topology(req: TopologyRequest):
    if not req.switches:
        raise HTTPException(400, "No switch IPs provided")
    return await build_topology(req.switches, req.community)


@router.post("/analyze", summary="Return full analyzed topology")
async def analyze(req: TopologyRequest):
    if not req.switches:
        raise HTTPException(400, "No switch IPs provided")
    return await build_topology(req.switches, req.community)