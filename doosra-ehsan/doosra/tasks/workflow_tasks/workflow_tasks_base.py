import logging

from celery import Task

from doosra import db as doosradb
from doosra.models import WorkflowRoot

LOGGER = logging.getLogger(__name__)


class WorkflowTasksBase(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error('{0!r} failed: {1!r}'.format(task_id, exc))
        workflow_root = doosradb.session.query(WorkflowRoot).filter_by(id=args[0]).first()
        if not workflow_root:
            return

        workflow_root.executor_running = False
        workflow_root.status = WorkflowRoot.STATUS_C_W_FAILURE
        doosradb.session.commit()
