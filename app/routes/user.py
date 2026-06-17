from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status

from database.database import get_session
from models.services.user import create_user, get_by_email
from models.services.balance import create as create_balance
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)
router = APIRouter()

SIGNUP_BONUS_CREDITS = 200.0  # стартовые кредиты на пробу (4 прогноза)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    plan: str = "free"


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(req: SignupRequest, session=Depends(get_session)) -> dict:
    if get_by_email(session, req.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    plan = req.plan if req.plan in ("free", "pro") else "free"
    user = create_user(session, req.email, req.password, plan=plan)
    create_balance(session, user.id, initial_amount=SIGNUP_BONUS_CREDITS)
    logger.info(f"Регистрация: {req.email}")
    return {"id": user.id, "email": user.email, "plan": user.plan, "credits": SIGNUP_BONUS_CREDITS}
