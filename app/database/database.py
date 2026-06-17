import os

from sqlmodel import SQLModel, Session, create_engine

from .config import get_settings
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)

# DATABASE_URL переопределяет драйвер (sqlite для тестов, psycopg2 для прода).
DATABASE_URL = os.environ.get("DATABASE_URL") or get_settings().DATABASE_URL_psycopg

# Пул соединений нужен только серверным БД; для sqlite его не задаём.
_engine_kwargs = {"echo": False}
if not DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update(pool_size=5, max_overflow=10)

engine = create_engine(DATABASE_URL, **_engine_kwargs)
logger.info(f"Движок БД создан ({DATABASE_URL.split(':')[0]})")


def get_session():
    """FastAPI-зависимость: выдаёт сессию и закрывает её по выходу."""
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Создаёт таблицы и идемпотентно засевает демо-пользователей."""
    # Импорт моделей регистрирует их в SQLModel.metadata до create_all.
    from models.User import User  # noqa: F401
    from models.Balance import Balance  # noqa: F401
    from models.Transactions import Transaction  # noqa: F401
    from models.Upload import Upload  # noqa: F401
    from models.ForecastJob import ForecastJob  # noqa: F401
    from models.ForecastResult import ForecastResult  # noqa: F401
    from models.services import user as user_service
    from models.services import balance as balance_service

    SQLModel.metadata.create_all(engine)
    logger.info("Таблицы БД созданы")

    session = next(get_session())
    try:
        if user_service.get_by_email(session, "Demo@mail.ru") is None:
            demo = user_service.create_user(session, "Demo@mail.ru", "demo", plan="pro")
            balance_service.create(session, user_id=demo.id, initial_amount=1000.0)
            admin = user_service.create_user(session, "Admin@demo.ru", "admin", is_admin=True)
            balance_service.create(session, user_id=admin.id, initial_amount=800.0)
            logger.info("Демо-пользователи засеяны")
        else:
            logger.info("Демо-пользователи уже существуют — сидинг пропущен")
    finally:
        session.close()
