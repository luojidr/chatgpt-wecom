import logging

from celery.signals import celeryd_init
from celery.signals import celeryd_after_setup
from celery.signals import beat_init
from celery.signals import task_internal_error

from ..conf import CeleryConfig
from ..core.webapp import run_with_thread

logger = logging.getLogger("celery.worker")


@beat_init.connect
def unregister_when_beat_init(sender, **kwargs):
    unregister_useless_tasks()
    logger.warning("Celery beat command is started!")

    if getattr(CeleryConfig, "CELERY_WEBAPP", False):
        run_with_thread(signal=kwargs.get('signal'))


@celeryd_after_setup.connect
def unregister_after_worker_setup(sender, instance, **kwargs):
    unregister_useless_tasks()

    if getattr(CeleryConfig, "CELERY_WEBAPP", False):
        run_with_thread(signal=kwargs.get('signal'))


@task_internal_error.connect
def handle_task_internal_error(sender, task_id, args, kwargs, request, einfo, **kw):
    """ Handle errors in tasks by signal, that is not internal logic error in task func code.
        Because the result of a failed task execution is stored in result_backend
    """
    logger.info("Sender<%s> was error: %s at task<%s>", sender, einfo, task_id)
    logger.error("TaskId: %s, args: %s, kwargs: %s, request: %s", task_id, args, kwargs, request)


@celeryd_init.connect
def bind_do_watch_task(sender, instance, conf, options, **kwargs):
    # from .utils.watcher import TaskWatcher
    # TaskWatcher()  # Auto to register task, then connect to consumer MQ message
    logger.warning("Celery worker command is started!")
    pass


def unregister_useless_tasks():
    """ Eliminate task of useless or not expected """
    from celery import current_app

    celery_tasks = current_app.tasks
    tasks = {task_name: task for task_name, task in celery_tasks.items()}

    for fun_name in CeleryConfig.CELERY_NOT_IMPORTS_TASKS:
        for complete_task_name, task in tasks.items():
            if fun_name == task.__name__:
                celery_tasks.unregister(complete_task_name)
