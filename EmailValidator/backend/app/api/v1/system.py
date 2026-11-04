from fastapi import APIRouter, Query, Request

from app.config import Settings
from app.models.schemas import DiagnosticsResponse
from app.services.diagnostics import run_diagnostics

router = APIRouter(prefix="/api/v1/system", tags=["system"])


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def get_diagnostics(request: Request, refresh: bool = Query(False)):
    settings = get_settings_dep(request)
    result = await run_diagnostics(settings, use_cache=not refresh)
    return DiagnosticsResponse(**result)
