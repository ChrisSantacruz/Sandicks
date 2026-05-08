"""Health check route."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Liveness probe")
async def health_check() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}
