from datetime import datetime, timezone

from sqlmodel import Column, DateTime, Field, SQLModel, func


def strftime():
    return func.strftime("%Y-%m-%d %H:%M:%S", "now")


def utc_now() -> datetime:
    """
    Return current UTC time as timezone-NAIVE datetime
    
    PostgreSQL TIMESTAMP WITHOUT TIME ZONE expects naive datetimes
    """
    return datetime.utcnow()


class BaseSqlModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
