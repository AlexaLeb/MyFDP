from typing import List

from sqlmodel import select

from models.Upload import Upload
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)


def create_upload(session, user_id: int, filename: str, row_count: int, sku_count: int,
                  status: str = "validated") -> Upload:
    upload = Upload(
        user_id=user_id,
        filename=filename,
        row_count=row_count,
        sku_count=sku_count,
        status=status,
    )
    session.add(upload)
    session.commit()
    session.refresh(upload)
    logger.info(f"Создан upload id={upload.id} user_id={user_id} rows={row_count} sku={sku_count}")
    return upload


def get_by_id(session, upload_id: int):
    return session.get(Upload, upload_id)


def list_for_user(session, user_id: int) -> List[Upload]:
    stmt = select(Upload).where(Upload.user_id == user_id).order_by(Upload.uploaded_at.desc())
    return session.exec(stmt).all()
