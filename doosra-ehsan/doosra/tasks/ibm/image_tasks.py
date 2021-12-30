import logging

from celery import chain

from doosra import db as doosradb
from doosra.common.consts import IN_PROGRESS, SUCCESS, FAILED
from doosra.common.utils import DELETING, DELETED
from doosra.ibm.common.consts import VALIDATION
from doosra.ibm.managers.exceptions import (
    IBMInvalidRequestError,
)
from doosra.models import IBMImage
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("image_tasks.py")


@celery.task(name="validate_ibm_images", base=IBMBaseTask, bind=True)
def task_validate_ibm_images(self, task_id, cloud_id, region, image_name):
    """Validate if instance images exist"""
    self.resource_name = image_name
    self.resource_type = 'images'
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )

    existing_image = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_images(name=image_name)
    if not existing_image:
        raise IBMInvalidRequestError(
            "IBM Image with name '{}' not found".format(image_name))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info(
        "IBM Image with name '{name}' validated successfully".format(name=image_name))


@celery.task(name="task_delete_image", base=IBMBaseTask, bind=True)
def task_delete_image(self, task_id, cloud_id, region, image_id):
    """
    This request deletes a Image
    @return:
    """

    ibm_image = doosradb.session.query(IBMImage).filter_by(id=image_id).first()
    if not ibm_image:
        return

    self.resource = ibm_image
    ibm_image.status = DELETING
    doosradb.session.commit()

    fetched_image = self.ibm_manager.rias_ops.fetch_ops.get_all_images(
        name=ibm_image.name, visibility="private", required_relations=False)
    if fetched_image:
        self.ibm_manager.rias_ops.delete_image(fetched_image[0])

    ibm_image.status = DELETED
    doosradb.session.delete(ibm_image)
    doosradb.session.commit()
    LOGGER.info("IBM image '{name}' deleted successfully on IBM Cloud".format(name=ibm_image.name))


@celery.task(name="task_delete_image_workflow", base=IBMBaseTask, bind=True)
def task_delete_image_workflow(self, task_id, cloud_id, region, image_id):
    """
    This request is workflow for the deletion of image
    @return:
    """
    workflow_steps = list()

    ibm_image = doosradb.session.query(IBMImage).filter_by(id=image_id).first()
    if not ibm_image:
        return

    workflow_steps.append(task_delete_image.si(
        task_id=task_id, cloud_id=cloud_id, region=region, image_id=image_id))
    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
