from datetime import datetime
from celery.utils.log import task_logger

from .app import celery_app


@celery_app.task
def test_celery_helper_demo(**kwargs):
    task_logger.info('test_celery_helper_demo test is successful! Now:%s', datetime.now())
