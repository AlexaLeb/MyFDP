from typing import Optional

from sqlalchemy import Index
from sqlmodel import SQLModel, Field, Relationship

from models.ForecastJob import ForecastJob


class ForecastResult(SQLModel, table=True):
    """Квантильный прогноз по одному SKU на один день."""

    __tablename__ = "forecast_results"
    # Основной паттерн запросов — выборка по job_id; внутри сортировка по sku/date.
    __table_args__ = (
        Index("ix_forecast_results_job_sku_date", "job_id", "sku_id", "date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="forecast_jobs.id", nullable=False)
    sku_id: str = Field(nullable=False)
    date: str = Field(nullable=False)  # ISO-дата прогнозируемого дня
    q10: float = Field(nullable=False)
    q50: float = Field(nullable=False)
    q90: float = Field(nullable=False)

    job: Optional[ForecastJob] = Relationship(back_populates="results")
