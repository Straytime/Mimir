from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["system"])


@router.get("/health")
async def get_health(
    check: Literal["readiness"] | None = Query(default=None),
) -> JSONResponse:
    del check
    return JSONResponse(
        content={
            "status": "ok",
            "service": "mimir-api",
            "version": "v1",
        },
        headers={"Cache-Control": "no-store"},
    )
