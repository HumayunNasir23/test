import logging

from doosra.common.consts import IN_PROGRESS, SUCCESS, FAILED
from doosra.ibm.common.consts import VALIDATION
from doosra.ibm.managers.exceptions import (
    IBMInvalidRequestError,
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask

LOGGER = logging.getLogger("acl_tasks.py")


@celery.task(name="validate_ibm_resource_group", base=IBMBaseTask, bind=True)
def task_validate_ibm_resource_group(self, task_id, cloud_id, region, resource_group):
    """Check if resource group is configured"""
    self.resource_type = 'resource_group'
    self.resource_name = resource_group
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    existing_resource_group = self.ibm_manager.resource_ops.fetch_ops.get_resource_groups(resource_group)
    if not existing_resource_group:
        raise IBMInvalidRequestError(
            "Resource Group with name '{name}' not configured".format(name=resource_group)
        )

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info(
        "IBM Resource group with name '{name}' validated successfully".format(name=resource_group))
