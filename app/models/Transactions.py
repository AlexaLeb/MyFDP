from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship

from models.User import User


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    tx_type: str = Field(sa_column_kwargs={"nullable": False})  # deposit / withdraw
    amount: Decimal = Field(nullable=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    description: Optional[str] = Field(default=None)

    user: Optional[User] = Relationship(back_populates="transactions")
