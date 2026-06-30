import os

# Должно быть выставлено ДО импорта api/database, иначе движок попробует psycopg2.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from sqlmodel import SQLModel, Session, create_engine, StaticPool
from fastapi.testclient import TestClient

# Импорт моделей наполняет SQLModel.metadata.
import models.User  # noqa: F401
import models.Balance  # noqa: F401
import models.Transactions  # noqa: F401
import models.Upload  # noqa: F401
import models.ForecastJob  # noqa: F401
import models.ForecastResult  # noqa: F401

from api import app
from database.database import get_session
import routes.upload as upload_route


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine, monkeypatch):
    def override_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    # Очередь мокаем — воркер/брокер в юнит-тестах не нужны.
    monkeypatch.setattr(upload_route, "publish_forecast_job", lambda payload: None)
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client):
    client.post("/api/users/signup", json={"email": "u@u.ru", "password": "pw"})
    client.post("/login/token", data={"username": "u@u.ru", "password": "pw"})
    return client
