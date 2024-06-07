import logging

from fkcookiecutter.celery_helper.app import celery_app


@celery_app.task
def test_flask_send_message(**kwargs):
    logging.warning(f'\t\tkwargs: {kwargs} test_flask_send_message running ......!')
    return kwargs

