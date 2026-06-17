from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship

from models.Upload import Upload


class ForecastJob(SQLModel, table=True):
    """Async-задача прогноза. Создаётся в статусе pending, обрабатывается воркером."""

    __tablename__ = "forecast_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    upload_id: int = Field(foreign_key="uploads.id", nullable=False)
    horizon: int = Field(nullable=False)  # 7 / 14 / 28
    status: str = Field(default="pending")  # pending / running / done / failed
    cost_credits: int = Field(default=50)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    finished_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    upload: Optional[Upload] = Relationship(back_populates="jobs")
    results: List["ForecastResult"] = Relationship(
        back_populates="job",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
