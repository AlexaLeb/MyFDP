import logging
from pathlib import Path


def get_logger(level=logging.INFO, logger_name: str = "default") -> logging.Logger:
    """Создаёт логгер с выводом в файл ./logs/myapp.log и в консоль."""
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Не добавляем хендлеры повторно при многократном импорте
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler("./logs/myapp.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
