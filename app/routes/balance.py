from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from database.database import get_session
from auth.auth import authenticate_cookie
from models.services.user import get_by_email
from models.services.balance import get_by_user_id as get_balance, create as create_balance
from models.services.transaction import create as create_transaction
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)
router = APIRouter()


class DepositRequest(BaseModel):
    amount: float


@router.get("/")
async def read_balance(user: str = Depends(authenticate_cookie), session=Depends(get_session)) -> dict:
    user_id = get_by_email(session, user).id
    balance = get_balance(session, user_id)
    if balance is None:
        balance = create_balance(session, user_id, 0.0)
    return {"user": user, "balance": balance.amount}


@router.post("/")
async def deposit(req: DepositRequest, user: str = Depends(authenticate_cookie),
                  session=Depends(get_session)) -> dict:
    if req.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")
    user_id = get_by_email(session, user).id
    if get_balance(session, user_id) is None:
        create_balance(session, user_id, 0.0)
    tx = create_transaction(session, user_id, "deposit", req.amount, description="top-up")
    balance = get_balance(session, user_id)
    logger.info(f"Пополнение {req.amount} для {user}")
    return {"user": user, "balance": balance.amount, "tx_id": tx.id}
