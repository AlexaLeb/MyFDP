from sqlmodel import SQLModel, Session, create_engine

from .config import get_settings
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)

# create_engine не открывает соединение сразу — только при первом запросе,
# поэтому импорт модуля безопасен даже без поднятого Postgres.
engine = create_engine(
    url=get_settings().DATABASE_URL_psycopg,
    echo=False,
    pool_size=5,
    max_overflow=10,
)
logger.info("Движок БД создан")


def get_session():
    """FastAPI-зависимость: выдаёт сессию и закрывает её по выходу."""
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Создаёт таблицы. Сидинг демо-данных добавляется в Фазе 2."""
    SQLModel.metadata.create_all(engine)
    logger.info("Таблицы БД созданы")
