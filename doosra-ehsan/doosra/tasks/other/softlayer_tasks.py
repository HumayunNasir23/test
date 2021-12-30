from doosra import db as doosradb
from doosra.common.consts import SUCCESS
from doosra.models import SoftlayerCloud
from doosra.models import SyncTask
from doosra.softlayer.utils import get_all_softlayer_cloud_accounts_images, list_softlayer_instance_hostnames
from doosra.softlayer.utils import get_classical_instance_details
from doosra.softlayer.utils import validate_softlayer_account
from doosra.tasks.celery_app import celery


@celery.task(name="validate_softlayer_cloud")
def task_validate_softlayer_cloud(cloud_id):
    softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(id=cloud_id).first()
    if not softlayer_cloud:
        return

    if validate_softlayer_account(softlayer_cloud):
        softlayer_cloud.status = "VALID"
        doosradb.session.commit()
    else:
        softlayer_cloud.status = "INVALID"
        doosradb.session.commit()


@celery.task(name="list_softlayer_instance_hostnames")
def task_list_softlayer_instance_hostnames(task_id, project_id):
    instances = list_softlayer_instance_hostnames(project_id)
    sync_task = doosradb.session.query(SyncTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    sync_task.status = SUCCESS
    sync_task.result = instances
    doosradb.session.commit()


@celery.task(name="get_classical_instance_details")
def task_get_classical_instance_details(task_id, project_id, instance_id):
    instance = get_classical_instance_details(project_id, instance_id)
    sync_task = doosradb.session.query(SyncTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    sync_task.status = SUCCESS
    sync_task.result = instance
    doosradb.session.commit()


@celery.task(name="get_softlayer_cloud_images")
def task_get_softlayer_cloud_images(task_id, project_id):
    images = get_all_softlayer_cloud_accounts_images(project_id)
    sync_task = doosradb.session.query(SyncTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    sync_task.status = SUCCESS
    sync_task.result = images
    doosradb.session.commit()
