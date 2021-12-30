import logging

from celery import chain

from doosra import db as doosradb
from doosra.common.consts import IN_PROGRESS, SUCCESS

from doosra.ibm.common.billing_utils import log_resource_billing, IBMResourceGroup
from doosra.ibm.common.consts import PROVISIONING
from doosra.common.utils import DELETING, DELETED, CREATING
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.models import (
    IBMPublicGateway,
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("public_gateway_tasks.py")


@celery.task(name="create_ibm_public_gateway", base=IBMBaseTask, bind=True)
def task_create_ibm_public_gateway(self, task_id, cloud_id, region, public_gateway_id, resource_group=None):
    """Create and configure public gateway"""

    ibm_public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(id=public_gateway_id).first()
    if not ibm_public_gateway:
        return
    ibm_public_gateway.status = CREATING

    if resource_group:
        ibm_resource_group = IBMResourceGroup(name=resource_group, cloud_id=cloud_id)
        ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
        ibm_public_gateway.ibm_resource_group = ibm_resource_group

    doosradb.session.commit()
    self.resource = ibm_public_gateway
    self.resource_type = "public_gateways"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_public_gateway = configure_and_save_obj_confs(self.ibm_manager, ibm_public_gateway)
    ibm_public_gateway = configured_public_gateway.make_copy().add_update_db(ibm_public_gateway.ibm_vpc_network)
    LOGGER.info(
        "IBM Public Gateway with name '{}' created successfully".format(ibm_public_gateway.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_public_gateway)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_public_gateway", base=IBMBaseTask, bind=True)
def task_delete_public_gateway(self, task_id, cloud_id, region, public_gateway_id):
    """
    This request deletes a public gateway
    @return:
    """
    ibm_public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(id=public_gateway_id).first()
    if not ibm_public_gateway:
        return

    self.resource = ibm_public_gateway
    ibm_public_gateway.status = DELETING
    doosradb.session.commit()

    fetched_public_gateway = self.ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
        name=ibm_public_gateway.name, vpc_name=ibm_public_gateway.ibm_vpc_network.name)

    if fetched_public_gateway:
        self.ibm_manager.rias_ops.delete_public_gateway(fetched_public_gateway[0])

    ibm_public_gateway.status = DELETED
    if ibm_public_gateway.floating_ip:
        doosradb.session.delete(ibm_public_gateway.floating_ip)
    doosradb.session.delete(ibm_public_gateway)
    doosradb.session.commit()
    LOGGER.info("IBM public gateway '{name}' deleted successfully on IBM Cloud".format(name=ibm_public_gateway.name))


@celery.task(name="task_detach_public_gateway_from_subnet", base=IBMBaseTask, bind=True)
def task_detach_public_gateway_from_subnet(self, task_id, cloud_id, region, public_gateway_id):
    """
    This request detaches the public gateway from the subnet
    @return:
    """

    ibm_public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(id=public_gateway_id).first()
    if not ibm_public_gateway:
        return

    self.resource = ibm_public_gateway

    fetched_public_gateway = self.ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(name=ibm_public_gateway.name)

    if fetched_public_gateway:
        for subnet in ibm_public_gateway.subnets:
            self.ibm_manager.rias_ops.detach_public_gateway_to_subnet(subnet)

    ibm_public_gateway.subnets = list()
    doosradb.session.commit()
    LOGGER.info("public gateway '{name}' successfully detached from subnet".format(name=ibm_public_gateway.name))


@celery.task(name="task_delete_public_gateway_workflow", base=IBMBaseTask, bind=True)
def task_delete_public_gateway_workflow(self, task_id, cloud_id, region, public_gateway_id):
    """
    This request deletes a public gateway and detach it from the subnet first.
    @return:
    """

    workflow_steps = list()

    ibm_public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(id=public_gateway_id).first()
    if not ibm_public_gateway:
        return

    workflow_steps.append(task_detach_public_gateway_from_subnet.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                                                    public_gateway_id=public_gateway_id))

    workflow_steps.append(task_delete_public_gateway.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                                        public_gateway_id=public_gateway_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
