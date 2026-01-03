from datetime import datetime, timezone

from sqlmodel import Column, DateTime, Field, SQLModel, func


def strftime():
    return func.strftime("%Y-%m-%d %H:%M:%S", "now")


def utc_now():
    return datetime.now(timezone.utc)


class BaseSqlModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
