import logging
from datetime import datetime, timedelta

from doosra import db as doosradb
from doosra.common.consts import DELETING
from doosra.models import GcpTask, IBMTask, MigrationTask, SyncTask, IBMCloud
from doosra.tasks.celery_app import celery

LOGGER = logging.getLogger(__name__)


@celery.task(name="delete_older_tasks")
def delete_older_tasks():
    tasks = IBMTask.query.filter(IBMTask.completed_at < datetime.utcnow() - timedelta(days=1)).all() + \
            GcpTask.query.filter(GcpTask.completed_at < datetime.utcnow() - timedelta(days=1)).all() + \
            MigrationTask.query.filter(MigrationTask.completed_at < datetime.utcnow() - timedelta(days=1)).all() + \
            SyncTask.query.filter(SyncTask.completed_at < datetime.utcnow() - timedelta(days=1)).all()

    for task in tasks:
        doosradb.session.delete(task)
        doosradb.session.commit()


@celery.task(name="delete_ibm_clouds")
def delete_ibm_clouds():
    clouds = doosradb.session.query(IBMCloud).filter(IBMCloud.status == DELETING).all()
    for cloud in clouds:
        try:
            doosradb.session.delete(cloud)
            doosradb.session.commit()
        except Exception as ex:
            LOGGER.exception(ex)
