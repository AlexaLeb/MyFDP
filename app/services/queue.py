"""Публикация задач прогноза в RabbitMQ (fire-and-forget).

В отличие от блокирующего RPC, API не ждёт результата: воркер пишет результат
и статус в БД, клиент опрашивает GET /api/v1/jobs/{id}.
"""
import json
import os

import pika

from logger.logging import get_logger

logger = get_logger(logger_name=__name__)

QUEUE_NAME = "prediction_tasks"
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")


def publish_forecast_job(payload: dict) -> None:
    """Публикует задачу в durable-очередь. Бросает исключение, если брокер недоступен."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
    )
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        logger.info(f"Задача job_id={payload.get('job_id')} опубликована в очередь")
    finally:
        connection.close()
