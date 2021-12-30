"""
~~~~~~~~~~~~~~~
tasks.celery_app.py
~~~~~~~~~~~~~~~

Create celery app for long running and parallel tasks
"""
import gc
import os
import logging
import logging_loki
import urllib
from celery.signals import after_task_publish, celeryd_init, worker_process_shutdown, task_postrun, task_failure

from celery.result import AsyncResult
from config import Config

from doosra.common.celery_app import create_celery_app
from doosra import create_app, db

LOGGER = logging.getLogger("celery_app.py")

app = create_app(os.getenv("FLASK_CONFIG") or "default")
celery = create_celery_app(app)


@celeryd_init.connect()
def configure_worker(conf=None, **kwargs):
    """Run App's prerequisite tasks"""
    from doosra.tasks.ibm.utils_tasks import task_group_clouds_by_api_key
    task_group_clouds_by_api_key.delay()


def initialize_loki(logger=None, loglevel=logging.INFO, *args, **kwargs):
    try:
        tag = os.environ.get('TAGS','worker')
        if tag in {"worker", "scheduler", "emailworker","syncworker"}:
            from multiprocessing import Queue
        elif tag in {"beatworker", "imageworker"}:
            from gevent.queue import Queue
        handler = logging_loki.LokiQueueHandler(
            Queue(-1),
            url="{0}/loki/api/v1/push".format(app.config["LOKI_URL"]),
            tags={"application": tag},
            auth=(app.config["LOKI_USERNAME"], app.config["LOKI_PASSWORD"]),
            version="1",
        )
        logger.addHandler(handler)
        logger.setLevel(loglevel)
    except:
        pass


def initialize_slack_logger(logger=None, *args, **kwargs):
    try:
        tag = os.environ.get('TAGS','worker')
        from slack_log_handler import SlackLogHandler
        slack_handler = SlackLogHandler(webhook_url=app.config["SLACK_WEBHOOK_URL"], channel=app.config["SLACK_CHANNEL"],
                                        format='{0} %(levelname)s - %(asctime)s - %(name)s - %(message)s'.format(tag))
        slack_handler.setLevel(logging.ERROR)
        logger.addHandler(slack_handler)
    except urllib.error.HTTPError:
        LOGGER.info("******************** Slack webhook is not working *********************")


if app.config["LOKI_LOGGING"]:
    from celery.signals import after_setup_logger

    after_setup_logger.connect(initialize_loki)


if app.config["SLACK_LOGGING"]:
    from celery.signals import after_setup_logger

    after_setup_logger.connect(initialize_slack_logger)


@after_task_publish.connect
def update_sent_state(sender=None, headers=None, **kwargs):
    """Change task status to SENT when task is published """
    # By default task status is PENDING if you get a non existing task by id
    # its status will be PENDING changing to SENT will confirm task exists

    task = celery.tasks.get(sender)
    backend = task.backend if task else celery.backend
    backend.store_result(headers["id"], None, "SENT")


def clean_task_from_backend(task_id, **kwargs):
    """Clean tasks entries from backend"""
    AsyncResult(task_id).forget()
    gc.collect()


task_postrun.connect(clean_task_from_backend)
task_failure.connect(clean_task_from_backend)


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    LOGGER.info("Shutting worker")
    with app.app_context():
        db.session.close()
        db.engine.dispose()
