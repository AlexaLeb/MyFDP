from fastapi import APIRouter, Depends, HTTPException, status

from database.database import get_session
from auth.auth import authenticate_cookie
from models.services.user import get_by_email
from models.services import forecast as forecast_service
from models.services import upload as upload_service
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)
router = APIRouter()


def _owned_job_or_404(session, job_id: int, user_email: str):
    job = forecast_service.get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    upload = upload_service.get_by_id(session, job.upload_id)
    user_id = get_by_email(session, user_email).id
    if upload is None or upload.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    return job


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: int, user: str = Depends(authenticate_cookie),
                         session=Depends(get_session)) -> dict:
    job = _owned_job_or_404(session, job_id, user)
    return {
        "job_id": job.id,
        "status": job.status,
        "horizon": job.horizon,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_message": job.error_message,
    }


@router.get("/results/{job_id}")
async def get_job_results(job_id: int, user: str = Depends(authenticate_cookie),
                          session=Depends(get_session)) -> dict:
    job = _owned_job_or_404(session, job_id, user)
    rows = forecast_service.get_results(session, job_id)
    return {
        "job_id": job.id,
        "status": job.status,
        "count": len(rows),
        "results": [
            {"sku_id": r.sku_id, "date": r.date, "q10": r.q10, "q50": r.q50, "q90": r.q90}
            for r in rows
        ],
    }
