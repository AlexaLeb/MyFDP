import time
from datetime import datetime

from fastapi import HTTPException, status
from jose import jwt, JWTError

from database.config import get_settings
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)
SECRET_KEY = get_settings().SECRET_KEY


def create_access_token(user: str) -> str:
    payload = {"user": user, "expires": time.time() + 3600}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_access_token(token: str) -> dict:
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1]
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    expire = data.get("expires")
    if expire is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token supplied")
    if datetime.utcnow() > datetime.utcfromtimestamp(expire):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token expired!")
    return data
