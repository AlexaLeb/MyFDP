"""Импорт всех моделей регистрирует мапперы SQLAlchemy целиком.

Без этого процесс, импортирующий лишь часть моделей (например воркер —
только ForecastJob/ForecastResult), падает на резолве строковых связей
(`Optional["Balance"]`), т.к. класс Balance не зарегистрирован в реестре.
Порядок — по зависимостям.
"""
from models.User import User  # noqa: F401
from models.Balance import Balance  # noqa: F401
from models.Transactions import Transaction  # noqa: F401
from models.Upload import Upload  # noqa: F401
from models.ForecastJob import ForecastJob  # noqa: F401
from models.ForecastResult import ForecastResult  # noqa: F401
