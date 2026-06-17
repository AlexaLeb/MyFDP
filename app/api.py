from contextlib import asynccontextmanager
from typing import Dict

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import init_db
from routes import login, user, balance, upload, jobs
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("Приложение запущено")
    yield
    logger.info("Завершение работы")


app = FastAPI(title="MFDP — квантильное прогнозирование спроса", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login.router, prefix="/login", tags=["login"])
app.include_router(user.router, prefix="/api/users", tags=["users"])
app.include_router(balance.router, prefix="/api/balance", tags=["balance"])
app.include_router(upload.router, prefix="/api/v1", tags=["forecast"])
app.include_router(jobs.router, prefix="/api/v1", tags=["forecast"])


@app.get("/api/v1/health", response_model=Dict[str, str], tags=["health"])
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True, log_level="info")
