import os

from celery import Celery
from celery.schedules import crontab
from importer import index_datasets

ruser = os.getenv("RABBITMQ_DEFAULT_USER")
rpass = os.getenv("RABBITMQ_DEFAULT_PASS")

app = Celery("tasks", broker=f"amqp://{ruser}:{rpass}@queue", backend="rpc://")


@app.task
def check():
    index_datasets()


app.conf.beat_schedule = {
    "run-me-every-night": {"task": "task.check", "schedule": crontab(minute=0, hour=0)}
}
