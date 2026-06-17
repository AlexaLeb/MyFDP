"""RabbitMQ-воркер: обрабатывает задачи прогноза асинхронно.

Масштабируется горизонтально: `docker-compose up --scale worker=N`. Все воркеры
слушают одну durable-очередь с prefetch_count=1, поэтому задачи распределяются
между ними по одной (competing consumers).
"""
import json
import os
import time

import pandas as pd
import pika

from database.database import get_session
from ml.predict import predict_csv
from models.services import forecast as forecast_service
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)

QUEUE_NAME = "prediction_tasks"
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")


def process_job(message: dict, session) -> int:
    """Обрабатывает одну задачу: running → predict → save → done.

    Возвращает число сохранённых строк. Бросает исключение при ошибке —
    обёртка-callback переведёт задачу в failed.
    """
    job_id = message["job_id"]
    horizon = int(message["horizon"])
    csv_data = message["csv_data"]

    forecast_service.update_status(session, job_id, "running")
    df = pd.DataFrame(csv_data)
    results = predict_csv(df, horizon)
    n = forecast_service.save_results(session, job_id, results)
    forecast_service.update_status(session, job_id, "done", finished=True)
    logger.info(f"Задача job_id={job_id} выполнена: {n} строк прогноза")
    return n


def callback(ch, method, properties, body):
    job_id = None
    session = next(get_session())
    try:
        message = json.loads(body)
        job_id = message.get("job_id")
        process_job(message, session)
    except Exception as err:
        logger.error(f"Ошибка обработки job_id={job_id}: {err}")
        if job_id is not None:
            try:
                forecast_service.update_status(
                    session, job_id, "failed", error_message=str(err)[:500], finished=True
                )
            except Exception as inner:
                logger.error(f"Не удалось пометить job_id={job_id} как failed: {inner}")
    finally:
        session.close()
    # ack в любом случае — не зацикливаем битую задачу (она помечена failed)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def create_connection(max_attempts: int = 10):
    for attempt in range(max_attempts):
        try:
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=100)
            )
            logger.info("Соединение с RabbitMQ установлено")
            return conn
        except pika.exceptions.AMQPConnectionError:
            logger.warning(f"Попытка {attempt+1}: RabbitMQ недоступен, повтор через 5с...")
            time.sleep(5)
    raise Exception("Не удалось подключиться к RabbitMQ")


def main():
    connection = create_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)  # по одной задаче на воркер — честное распределение
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    logger.info("Воркер запущен, ожидаем задачи...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()


if __name__ == "__main__":
    logger.info("Старт воркера")
    while True:
        try:
            main()
        except Exception as err:
            logger.error(f"Воркер упал, перезапуск через 5с: {err}")
            time.sleep(5)
