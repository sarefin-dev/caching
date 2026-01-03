# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import orders, payments, health
from app.core.config import get_settings
from app.core.database import check_db_connection
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting application...")
    try:
        await check_db_connection()
        logger.info("Database connectivity verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    yield
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Production-ready payment service with reliability patterns",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(payments.router, prefix="/api", tags=["Payments"])
app.include_router(orders.router, prefix="/api", tags=["Orders"])
app.include_router(health.router, prefix="/health", tags=["Orders"])

# CORS Middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.app_name, "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs",
        "health": "/health",
    }
