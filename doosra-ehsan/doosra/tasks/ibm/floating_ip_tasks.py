import logging

from celery import chain

from doosra import db as doosradb
from doosra.common.utils import CREATED, DELETING, DELETED, IN_PROGRESS, SUCCESS
from doosra.ibm.common.consts import PROVISIONING, VALIDATION
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.ibm.managers.exceptions import (
    IBMInvalidRequestError,
)
from doosra.models import (
    IBMFloatingIP,
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("floating_ip_tasks.py")


@celery.task(name="validate_ibm_floating_ips", base=IBMBaseTask, bind=True)
def task_validate_ibm_floating_ip(self, task_id, cloud_id, region, floating_ip):
    """Validate if floating IP already exists"""
    self.resource_name = floating_ip["name"]
    self.resource_type = "floating_ips"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    existing_floating_ip = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_floating_ips(name=floating_ip["name"])
    if existing_floating_ip:
        raise IBMInvalidRequestError(
            "Floating IP '{name}' already exists".format(name=floating_ip["name"]))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )


@celery.task(name="configure_ibm_floating_ip", base=IBMBaseTask, bind=True)
def task_create_ibm_floating_ip(self, task_id, cloud_id, region, floating_ip_id):
    """Create and configure floating ip"""

    ibm_floating_ip = doosradb.session.query(IBMFloatingIP).filter_by(id=floating_ip_id).first()
    self.resource = ibm_floating_ip
    self.resource_type = "floating_ips"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_floating_ip = configure_and_save_obj_confs(self.ibm_manager, ibm_floating_ip)
    ibm_floating_ip.status = CREATED
    ibm_floating_ip.resource_id = configured_floating_ip.resource_id
    ibm_floating_ip = configured_floating_ip.make_copy().add_update_db()
    LOGGER.info("IBM Floating IP with name '{name}' created successfully".format(name=ibm_floating_ip.name))
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="delete_ibm_floating_ip", base=IBMBaseTask, bind=True)
def task_delete_ibm_floating_ip(self, task_id, cloud_id, region, floating_ip_id):
    """
    This request deletes a floating ip
    @return:
    """
    ibm_floating_ip = doosradb.session.query(IBMFloatingIP).filter_by(id=floating_ip_id).first()
    if not ibm_floating_ip:
        return

    self.resource = ibm_floating_ip
    ibm_floating_ip.status = DELETING
    doosradb.session.commit()

    fetched_floating_ip = self.ibm_manager.rias_ops.fetch_ops.get_all_floating_ips(name=ibm_floating_ip.name)

    if fetched_floating_ip:
        self.ibm_manager.rias_ops.delete_floating_ip(fetched_floating_ip[0])

    ibm_floating_ip.status = DELETED
    doosradb.session.delete(ibm_floating_ip)
    doosradb.session.commit()

    LOGGER.info(
        "IBM Floating IP with address '{address}' deleted successfully on IBM Cloud".format(
            address=ibm_floating_ip.address))


@celery.task(name="task_delete_ibm_floating_ip_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_floating_ip_workflow(self, task_id, cloud_id, region, floating_ip_id):
    """
    This request is workflow for deletion of floating ip
    @return:
    """
    workflow_steps = list()

    ibm_floating_ip = doosradb.session.query(IBMFloatingIP).filter_by(id=floating_ip_id).first()
    if not ibm_floating_ip:
        return

    workflow_steps.append(task_delete_ibm_floating_ip.si(task_id=task_id, cloud_id=cloud_id,
                                                         region=region, floating_ip_id=floating_ip_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
