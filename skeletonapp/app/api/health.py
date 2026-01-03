# app/api/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.core.database import get_session
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health/liveness")
async def liveness():
    """Liveness probe - is app running?"""
    return {"status": "alive"}


@router.get("/health/readiness")
async def readiness(session: AsyncSession = Depends(get_session)):
    """Readiness probe - is app ready to serve traffic?"""
    checks = {}
    
    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"
    
    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"
    
    all_healthy = all(v == "healthy" for v in checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }