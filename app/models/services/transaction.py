from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlmodel import select

from models.Balance import Balance
from models.Transactions import Transaction
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)


def create(session, user_id: int, tx_type: str, amount, description: Optional[str] = None) -> Transaction:
    """Создаёт транзакцию и атомарно меняет баланс. tx_type: deposit | withdraw."""
    # SELECT ... FOR UPDATE: строка баланса блокируется до конца транзакции,
    # параллельные списания не читают один и тот же остаток (double spend).
    # SQLite (тесты) молча игнорирует FOR UPDATE — там гонок нет.
    balance = session.exec(
        select(Balance).where(Balance.user_id == user_id).with_for_update()
    ).first()
    if balance is None:
        raise ValueError("Balance not found")

    amount = Decimal(str(amount))
    if tx_type == "withdraw":
        if Decimal(str(balance.amount)) < amount:
            logger.error(f"Недостаточно средств: user_id={user_id}")
            raise ValueError("Insufficient funds")
        balance.amount = float(Decimal(str(balance.amount)) - amount)
    elif tx_type == "deposit":
        balance.amount = float(Decimal(str(balance.amount)) + amount)
    else:
        raise ValueError("Invalid transaction type")

    balance.updated_at = datetime.utcnow()
    tx = Transaction(
        user_id=user_id,
        tx_type=tx_type,
        amount=amount,
        timestamp=datetime.utcnow(),
        description=description,
    )
    session.add(tx)
    session.add(balance)
    session.commit()
    session.refresh(tx)
    logger.info(f"Транзакция {tx_type} {amount} user_id={user_id}")
    return tx


def list_transactions(session, user_id: int) -> List[Transaction]:
    stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(
        Transaction.timestamp.desc()
    )
    return session.exec(stmt).all()
