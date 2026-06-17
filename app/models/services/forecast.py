from datetime import datetime
from typing import List, Optional

from sqlmodel import select

from models.ForecastJob import ForecastJob
from models.ForecastResult import ForecastResult
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)


def create_job(session, upload_id: int, horizon: int, cost_credits: int = 50) -> ForecastJob:
    job = ForecastJob(upload_id=upload_id, horizon=horizon, cost_credits=cost_credits, status="pending")
    session.add(job)
    session.commit()
    session.refresh(job)
    logger.info(f"Создана задача job_id={job.id} upload_id={upload_id} horizon={horizon}")
    return job


def get_job(session, job_id: int) -> Optional[ForecastJob]:
    return session.get(ForecastJob, job_id)


def update_status(session, job_id: int, status: str, error_message: Optional[str] = None,
                  finished: bool = False) -> Optional[ForecastJob]:
    job = session.get(ForecastJob, job_id)
    if job is None:
        return None
    job.status = status
    if error_message is not None:
        job.error_message = error_message
    if finished:
        job.finished_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    logger.info(f"Задача job_id={job_id} → {status}")
    return job


def save_results(session, job_id: int, rows: List[dict]) -> int:
    """rows: [{sku_id, date, q10, q50, q90}]. Возвращает число сохранённых строк."""
    objects = [
        ForecastResult(
            job_id=job_id,
            sku_id=str(r["sku_id"]),
            date=str(r["date"]),
            q10=float(r["q10"]),
            q50=float(r["q50"]),
            q90=float(r["q90"]),
        )
        for r in rows
    ]
    session.add_all(objects)
    session.commit()
    logger.info(f"Сохранено {len(objects)} результатов для job_id={job_id}")
    return len(objects)


def get_results(session, job_id: int) -> List[ForecastResult]:
    stmt = select(ForecastResult).where(ForecastResult.job_id == job_id).order_by(
        ForecastResult.sku_id, ForecastResult.date
    )
    return session.exec(stmt).all()
