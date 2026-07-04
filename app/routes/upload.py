import io

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from database.database import get_session
from auth.auth import authenticate_cookie
from ml.features import validate_csv
from models.services.user import get_by_email
from models.services.balance import get_by_user_id as get_balance, create as create_balance
from models.services.transaction import create as create_transaction
from models.services import upload as upload_service
from models.services import forecast as forecast_service
from services.queue import publish_forecast_job
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)
router = APIRouter()

FORECAST_COST = 50
ALLOWED_HORIZONS = (7, 14, 28)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_csv(
    file: UploadFile = File(...),
    horizon: int = Form(...),
    user: str = Depends(authenticate_cookie),
    session=Depends(get_session),
) -> dict:
    """Принимает CSV (date, sku_id, sales), ставит задачу прогноза в очередь.

    Возвращает job_id сразу — результат опрашивается через GET /api/v1/jobs/{id}.
    CSV в БД не сохраняется, передаётся напрямую воркеру через очередь.
    """
    if horizon not in ALLOWED_HORIZONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon должен быть одним из {ALLOWED_HORIZONS}",
        )

    # 1) Парсинг CSV
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось прочитать CSV")

    # 2) Валидация (колонки, >=60 дней на SKU)
    try:
        row_count, sku_count = validate_csv(df)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # 3) Проверка кредитов
    user_id = get_by_email(session, user).id
    balance = get_balance(session, user_id)
    if balance is None:
        balance = create_balance(session, user_id, 0.0)
    if balance.amount < FORECAST_COST:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Недостаточно кредитов (нужно {FORECAST_COST}, есть {balance.amount})",
        )

    # 4) Создаём upload + job, списываем кредиты.
    # Списание может упасть при гонке параллельных загрузок (баланс проверяется
    # повторно под блокировкой строки) — тогда помечаем job failed и отдаём 402.
    upload_row = upload_service.create_upload(session, user_id, file.filename, row_count, sku_count)
    job = forecast_service.create_job(session, upload_row.id, horizon, cost_credits=FORECAST_COST)
    try:
        create_transaction(session, user_id, "withdraw", FORECAST_COST, description=f"forecast job {job.id}")
    except ValueError:
        forecast_service.update_status(session, job.id, "failed", error_message="insufficient credits")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Недостаточно кредитов (нужно {FORECAST_COST})",
        )

    # 5) Публикуем задачу. CSV → payload (не в БД).
    df_payload = df[["date", "sku_id", "sales"]].copy()
    df_payload["date"] = pd.to_datetime(df_payload["date"]).dt.date.astype(str)
    payload = {
        "job_id": job.id,
        "user_id": user_id,
        "horizon": horizon,
        "csv_data": df_payload.to_dict(orient="records"),
    }
    try:
        publish_forecast_job(payload)
    except Exception as err:
        logger.error(f"Публикация задачи {job.id} не удалась: {err}")
        forecast_service.update_status(session, job.id, "failed", error_message="queue unavailable")
        create_transaction(session, user_id, "deposit", FORECAST_COST, description=f"refund job {job.id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Очередь недоступна, кредиты возвращены",
        )

    return {
        "job_id": job.id,
        "status": job.status,
        "row_count": row_count,
        "sku_count": sku_count,
        "horizon": horizon,
    }
