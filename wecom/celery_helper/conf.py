import os.path
import logging

import environs
from kombu import Exchange, Queue
from celery.schedules import crontab

from .core.autodiscover import autodiscover_task_imports, autodiscover_task_list

__all__ = ["CeleryConfig"]


def get_dotenv_config_path() -> str:
    package_name = __package__.split('.')[0]
    current_path_list = __file__.split(os.sep)
    index = current_path_list.index(package_name)
    project_path = os.sep.join(current_path_list[: index + 1])

    return os.path.join(project_path, 'config', '.env', 'celery')


def load_environs():
    env = environs.Env()
    env.read_env(path=get_dotenv_config_path())


load_environs()
logging.warning("CeleryConfig go into env[%s]", os.getenv("APP_ENV", "DEV"))


class HelperConfig:
    """ User-Defined Configuration """
    APP_ENV = os.getenv("APP_ENV", "DEV")
    APP_NAME = os.getenv("APP_NAME")

    # Send Raw Message to `AMPQ` config
    CELERY_NATIVE_AMQP = "%s.hooks.amqp:Amqp" % __name__.rsplit(".", 1)[0]

    # Each task function can save separately execution results to a different backend (Redis, DB, filesystem etc.)
    # CELERY_TASK_BACKENDS = {
    #     'redis': "redis://{user}:{password}@{host}:{port}/{db}".format(
    #         user=os.getenv("REDIS:USER"), password=os.getenv("REDIS:PASSWORD"),
    #         host=os.getenv("REDIS:HOST"), port=os.getenv("REDIS:PORT"), db=os.getenv("REDIS:DB0"),
    #     ),
    #
    #     'flask_db': 'flask-db',          # Not implement: flask_celery_results.backends:DatabaseBackend
    # }

    CELERY_TASK_WATCHER = False  # Watch task to monitor


class BaseCeleryConfig:
    """ Celery Standard basic configuration """
    CELERY_TIMEZONE = "Asia/Shanghai"
    CELERY_ENABLE_UTC = False

    # 任务发送完成是否需要确认，对性能会稍有影响
    CELERY_ACKS_LATE = True

    # 非常重要, 有些情况下可以防止死锁 (celery4.4.7可能没有这个配置)
    CELERYD_FORCE_EXECV = True

    # 并发worker数, 也是命令行 -c 指定的数目
    # CELERYD_CONCURRENCY = os.cpu_count()

    # 每个 worker 执行了多少个任务就死掉，建议数量大一些, 一定程度上可以解决内存泄漏的情况
    CELERYD_MAX_TASKS_PER_CHILD = 100

    # 表示每个 worker 预取多少个消息, 默认每个启动的 worker 下有 cpu_count 个子 worker 进程
    # 所有 worker 预取消息数量: cpu_count * CELERYD_PREFETCH_MULTIPLIER
    CELERYD_PREFETCH_MULTIPLIER = 5

    # celery日志存储位置 (celery4.4.7可能没有这个配置)
    # CELERYD_LOG_FILE = "/data/logs/myproject/circle_celery.log"

    CELERY_ACCEPT_CONTENT = ['json', ]      # 任务接受的序列化类型
    CELERY_SERIALIZER = "json"
    CELERY_TASK_SERIALIZER = 'json'         # 指定任务的序列化方式
    CELERY_RESULT_SERIALIZER = "json"       # 任务执行结果序列化方式

    # `flask-celery-results` (该库暂时没有实现)
    # CELERY_RESULT_BACKEND = 'flask-db'
    CELERY_RESULT_BACKEND = 'redis://@127.0.0.1:6379/0'  # Celery default backend

    CELERY_RESULT_EXPIRES = 24 * 60 * 60  # 任务结果的过期时间，定期(periodic)任务好像会自动清理

    # `flask-celery-beat` celery_helper.beat.schedulers:DatabaseScheduler (测试中)
    CELERYBEAT_SCHEDULER = "%s.hooks.schedulers:DatabaseScheduler" % __package__

    # CELERY_TRACK_STARTED = True

    # 拦截根日志配置，默认true，先前所有的logger的配置都会失效，可以通过设置false禁用定制自己的日志处理程序
    CELERYD_HIJACK_ROOT_LOGGER = False
    CELERYD_LOG_COLOR = True  # 是否开启不同级别的颜色标记，默认开启

    # 设置celery全局的日志格式；默认格式："[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    # CELERYD_LOG_FORMAT = ''
    # 设置任务日志格式，默认："[%(asctime)s: %(levelname)s/%(processName)s [%(task_name)s(%(task_id)s)] %(message)s"
    # CELERYD_TASK_LOG_FORMAT = ''

    # 去掉心跳机制
    BROKER_HEARTBEAT = 0

    # 限制任务的执行频率
    # CELERY_ANNOTATIONS = {'tasks.add': {'rate_limit': '10/s'}}  # 限制tasks模块下的add函数，每秒钟只能执行10次
    # CELERY_ANNOTATIONS = {'*': {'rate_limit': '10/s'}}  # 限制所有的任务的刷新频率

    # CELERY_TASK_RESULT_EXPIRES = 1200     # 任务过期时间, celery任务执行结果的超时时间
    # CELERYD_TASK_TIME_LIMIT = 60          # 单个任务的运行时间限制，否则执行该任务的worker将被杀死，任务移交给父进程
    # CELERY_DISABLE_RATE_LIMITS = True     # 关闭限速
    # CELERY_MESSAGE_COMPRESSION = 'zlib'           # 压缩方案选择，可以是zlib, bzip2，默认是发送没有压缩的数据

    # 设置默认的队列名称，如果一个消息不符合其他的队列就会放在默认队列里面，如果什么都不设置的话，数据都会发送到默认的队列中
    # CELERY_DEFAULT_QUEUE = "default"

    # Periodic Tasks
    CELERYBEAT_SCHEDULE = {
        # Special task: celery helper demo task
        "test_celery_helper_demo": {
            'task': '%s.demo.test_celery_helper_demo' % __package__,
            'schedule': crontab(),  # Execute per minute
            'args': (),
            'kwargs': dict(),
        },
    }


class QueueRouteConfig(object):
    """ Router config of RabbitMQ Queue """
    # User defined: CELERY_NOT_IMPORTS_TASKS => Tasks that do not need to be performed(useless task)
    if os.getenv("APP_ENV", "DEV") == 'DEV':
        CELERY_NOT_IMPORTS_TASKS = []
    else:
        CELERY_NOT_IMPORTS_TASKS = []

    CELERY_IMPORTS = autodiscover_task_imports()

    # Custom: expected_task_list => get fully expected celery tasks
    expected_task_list = autodiscover_task_list(CELERY_IMPORTS, not_import_tasks=CELERY_NOT_IMPORTS_TASKS)

    CELERY_QUEUES = [
        Queue(
            name=task_item["task_name"] + "_q",  # task name as queue name
            exchange=Exchange(task_item["task_name"] + "_exc"),  # task name as exchange name
            routing_key=task_item["task_name"] + "_rk",  # task name as routing_key name
        )
        for task_item in expected_task_list
    ]

    CELERY_ROUTES = {
        # The full path of the task(accurate to the function name): {queue_name, routing_key}
        # eg:
        #     {
        #         'myproject.apps.ding_talk.tasks.task_test_module.send_message': {
        #             'queue': 'send_message_q',
        #             'routing_key': 'send_message_rk',
        #         }
        #     }
        task_item["complete_name"]: {
            "queue": task_item["task_name"] + "_q",
            "routing_key": task_item["task_name"] + "_rk",
        }
        for task_item in expected_task_list
    }


class CeleryConfig(BaseCeleryConfig, HelperConfig, QueueRouteConfig):
    if os.getenv("APP_ENV", "DEV") == 'DEV':
        BROKER_URL = "redis://{user}:{pwd}@{host}:{port}/{virtual_host}".format(
            user=os.getenv("REDIS:DEV:USER"), pwd=os.getenv("REDIS:DEV:PASSWORD"),
            host=os.getenv("REDIS:DEV:HOST"), port=os.getenv("REDIS:DEV:PORT"),
            virtual_host=os.getenv("REDIS:DEV:VIRTUAL_HOST"),
        )

    else:
        BROKER_URL = "amqp://{user}:{pwd}@{host}:{port}/{virtual_host}".format(
            user=os.getenv("RABBITMQ:PRD:USER"), pwd=os.getenv("RABBITMQ:PRD:PASSWORD"),
            host=os.getenv("RABBITMQ:PRD:HOST"), port=os.getenv("RABBITMQ:PRD:PORT"),
            virtual_host=os.getenv("RABBITMQ:PRD:VIRTUAL_HOST"),
        )

