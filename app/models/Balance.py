from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship

from models.User import User


class Balance(SQLModel, table=True):
    __tablename__ = "balances"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    amount: float = Field(default=0.0)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: Optional[User] = Relationship(back_populates="balance")

    def deposit(self, amount: float) -> None:
        self.amount += amount

    def withdraw(self, amount: float) -> None:
        if self.amount >= amount:
            self.amount -= amount
        else:
            raise Exception("Недостаточно средств для списания")

    def get_amount(self) -> float:
        return self.amount
