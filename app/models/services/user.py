from models.User import User
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)


def create_user(session, email: str, password: str, plan: str = "free", is_admin: bool = False):
    user = User(email=email, hashed_password="", plan=plan)
    user.set_password(password)
    user.is_admin = is_admin
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"Создан пользователь {email} (plan={plan})")
    return user


def get_all_users(session):
    return session.query(User).all()


def get_by_email(session, email: str):
    return session.query(User).filter_by(email=email).first()
