from typing import Optional, List

import bcrypt
from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column_kwargs={"unique": True, "nullable": False})
    hashed_password: str = Field(sa_column_kwargs={"nullable": False})
    plan: str = Field(default="free")  # free / pro
    is_admin: bool = Field(default=False, sa_column_kwargs={"default": False})

    balance: Optional["Balance"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    uploads: List["Upload"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def set_password(self, password: str) -> None:
        self.hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
