from __future__ import absolute_import

import logging
from importlib import import_module
from collections import OrderedDict

from celery import Celery
from celery import platforms

from .conf import CeleryConfig
from .hooks.context import TaskContext

__all__ = ["app", 'celery_app']

beat_cls = "%s.hooks.beat:Beat" % __name__.rsplit(".", 1)[0]

main = CeleryConfig.APP_NAME or __name__
app = Celery(main=main + '_celery', task_cls=TaskContext)
# app.set_current()
platforms.C_FORCE_ROOT = True       # celery不能用root用户启动问题

# This means that you don't have to use multiple configuration files, and instead configure Celery directly from the
# Django settings. You can pass the object directly here, but using a string is better since then the worker doesn't
# have to serialize the object.
# Not use `namespace` param, because of effect celery standard configuration
# https://docs.celeryproject.org/en/v4.4.7/userguide/configuration.html
app.config_from_object(obj=CeleryConfig)

# With the line above Celery will automatically discover tasks in reusable apps if you define all tasks in a separate
# tasks.py module. The tasks.py should be in dir which is added to INSTALLED_APP in settings.py. So you do not have
# to manually add the individual modules to the CELERY_IMPORTS in settings.py.
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
# app.autodiscover_tasks()

# 设置 BROKER_URL 后, 启动 worker 后可以探测所有任务,未启动无法探测
# i = app.control.inspect()  # 探测所有 worker
# print(i.registered_tasks())

# Pprint config
tips_kwargs = OrderedDict(
    broker_url=app.conf.broker_url,
    beat_scheduler=app.conf.beat_scheduler,
    beat_cls=beat_cls,
    amqp_cls=CeleryConfig.CELERY_NATIVE_AMQP
)
tips_msg = "\n\t".join(["%s: {%s}" % (k, k) for k in tips_kwargs])
logging.warning(('===>>> Celery Important Config:\n\t' + tips_msg).format(**tips_kwargs))


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))  # dumps its own request information


# Dynamic import celery signals
import_module('.hooks.signals', package=__package__)
celery_app = app
