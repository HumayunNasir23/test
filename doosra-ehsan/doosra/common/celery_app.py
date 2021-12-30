"""
~~~~~~~~~
celery_app.py
~~~~~~~~~
Implement create celery app function
"""

import os

from celery import Celery

from doosra import create_app


def create_celery_app(app=None):
    """Create celery app using Flask app configurations and db"""

    # todo Remove flask app dependency

    app = app or create_app(os.getenv("FLASK_CONFIG") or "default")
    celery = Celery(__name__, broker=app.config["CELERY_BROKER_URL"])
    celery.conf.update(app.config)
    Taskbase = celery.Task

    class ContextTask(Taskbase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return Taskbase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
