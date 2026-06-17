from models.Balance import Balance
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)


def create(session, user_id: int, initial_amount: float = 0.0) -> Balance:
    balance = Balance(user_id=user_id, amount=initial_amount)
    session.add(balance)
    session.commit()
    session.refresh(balance)
    logger.info(f"Создан баланс для user_id={user_id}")
    return balance


def update_balance(session, balance: Balance) -> Balance:
    session.add(balance)
    session.commit()
    session.refresh(balance)
    return balance


def get_by_user_id(session, user_id: int):
    return session.query(Balance).filter_by(user_id=user_id).first()
