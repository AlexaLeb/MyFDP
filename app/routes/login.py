from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from auth.jwt_handler import create_access_token
from auth.hash_password import HashPassword
from database.database import get_session
from database.config import get_settings
from models.services import user as UsersService
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)
settings = get_settings()
router = APIRouter()
hash_password = HashPassword()


@router.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session=Depends(get_session),
) -> dict:
    user = UsersService.get_by_email(session, form_data.username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")

    if not hash_password.verify_hash(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(user.email)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=3600,
    )
    logger.info(f"Вход: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(settings.COOKIE_NAME)
    return {"message": "logged out"}
