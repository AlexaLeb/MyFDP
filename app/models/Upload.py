from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship

from models.User import User


class Upload(SQLModel, table=True):
    """Метаданные загруженного CSV. Сам файл в БД НЕ хранится."""

    __tablename__ = "uploads"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    filename: str = Field(nullable=False)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    row_count: int = Field(default=0)
    sku_count: int = Field(default=0)
    status: str = Field(default="received")  # received / validated / rejected

    user: Optional[User] = Relationship(back_populates="uploads")
    jobs: List["ForecastJob"] = Relationship(
        back_populates="upload",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
