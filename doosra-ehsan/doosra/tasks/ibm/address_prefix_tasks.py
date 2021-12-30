import logging

from celery import chain

from doosra import db as doosradb

from doosra.ibm.common.billing_utils import log_resource_billing
from doosra.ibm.common.consts import PROVISIONING
from doosra.common.consts import CREATED, DELETING, DELETED, CREATING, IN_PROGRESS, SUCCESS
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.models import (
    IBMAddressPrefix,
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("address_prefix_tasks.py")


@celery.task(name="add_ibm_address_prefix", base=IBMBaseTask, bind=True)
def task_add_ibm_address_prefix(self, task_id, cloud_id, region, addr_prefix_id):
    """Create and configure address prefixes"""

    ibm_address_prefix = doosradb.session.query(IBMAddressPrefix).filter_by(id=addr_prefix_id).first()
    if not ibm_address_prefix:
        return

    ibm_address_prefix.status = CREATING
    doosradb.session.commit()
    self.resource = ibm_address_prefix
    self.resource_type = "address_prefixes"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_address_prefix = configure_and_save_obj_confs(self.ibm_manager, ibm_address_prefix)
    ibm_address_prefix.status = CREATED
    ibm_address_prefix.resource_id = configured_address_prefix.resource_id
    doosradb.session.commit()
    LOGGER.info(
        "IBM Address Prefix with name '{}' created successfully".format(
            ibm_address_prefix.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_address_prefix)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_address_prefix", base=IBMBaseTask, bind=True)
def task_delete_address_prefix(self, task_id, cloud_id, region, addr_prefix_id):
    """
    This request deletes a prefix. This operation cannot be reversed.
    @return:
    """

    ibm_address_prefix = doosradb.session.query(IBMAddressPrefix).filter_by(id=addr_prefix_id).first()
    if not ibm_address_prefix:
        return

    self.resource = ibm_address_prefix
    ibm_address_prefix.status = DELETING
    doosradb.session.commit()

    fetched_address_prefix = self.ibm_manager.rias_ops.fetch_ops.get_all_vpc_address_prefixes(
        name=ibm_address_prefix.name,
        vpc_id=ibm_address_prefix.ibm_vpc_network.resource_id
    )

    if fetched_address_prefix:
        self.ibm_manager.rias_ops.delete_address_prefix(
            fetched_address_prefix[0],
            vpc_id=ibm_address_prefix.ibm_vpc_network.resource_id
        )

    doosradb.session.delete(ibm_address_prefix)
    ibm_address_prefix.status = DELETED
    doosradb.session.commit()
    LOGGER.info("Address prefix '{name}' deleted successfully on IBM Cloud".format(name=ibm_address_prefix.name))


@celery.task(name="task_delete_address_prefix_workflow", base=IBMBaseTask, bind=True)
def task_delete_address_prefix_workflow(self, task_id, cloud_id, region, addr_prefix_id):
    """
    This request is workflow for the deletion of address prefix
    @return:
    """
    workflow_steps = list()

    ibm_address_prefix = doosradb.session.query(IBMAddressPrefix).filter_by(id=addr_prefix_id).first()
    if not ibm_address_prefix:
        return

    workflow_steps.append(task_delete_address_prefix.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                                        addr_prefix_id=addr_prefix_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
