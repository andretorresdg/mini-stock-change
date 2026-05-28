"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/ready")
def readiness() -> dict[str, str]:
    """Readiness probe."""
    return {"status": "ok"}
