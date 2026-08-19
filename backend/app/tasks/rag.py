import time

from app.celery_app import celery_app


@celery_app.task(name="long_running_task")
def long_running_task(x: int, y: int):
    time.sleep(5)
    return x + y
