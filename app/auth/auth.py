from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .jwt_handler import verify_access_token
from services.cookieauth import OAuth2PasswordBearerWithCookie

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/token", auto_error=False)
oauth2_scheme_cookie = OAuth2PasswordBearerWithCookie(tokenUrl="/login/token")


async def authenticate(token: str = Depends(oauth2_scheme)) -> str:
    """REST-аутентификация по заголовку Authorization: Bearer."""
    if not token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sign in for access")
    return verify_access_token(token)["user"]


async def authenticate_cookie(token: str = Depends(oauth2_scheme_cookie)) -> str:
    """Аутентификация по cookie (используется UI и REST-клиентом Streamlit)."""
    if not token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sign in for access")
    token = token.removeprefix("Bearer ")
    return verify_access_token(token)["user"]
