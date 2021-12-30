import logging

from celery import chain

from doosra import db as doosradb
from doosra.common.consts import IN_PROGRESS, SUCCESS

from doosra.ibm.common.billing_utils import log_resource_billing
from doosra.ibm.common.consts import PROVISIONING
from doosra.common.utils import DELETING, DELETED, CREATING
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.models import (
    IBMSecurityGroup,
    IBMSecurityGroupRule)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("security_group_tasks.py")


@celery.task(name="add_ibm_security_group", base=IBMBaseTask, bind=True)
def task_add_ibm_security_group(self, task_id, cloud_id, region, security_group_id):
    """Create and configure Security Group"""

    ibm_security_group = doosradb.session.query(IBMSecurityGroup).filter_by(id=security_group_id).first()
    if not ibm_security_group:
        return
    ibm_security_group.status = CREATING
    doosradb.session.commit()
    self.resource = ibm_security_group
    self.resource_type = "security_groups"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_security_group = configure_and_save_obj_confs(self.ibm_manager, ibm_security_group)
    ibm_security_group = configured_security_group.make_copy().add_update_db(ibm_security_group.ibm_vpc_network)
    LOGGER.info(
        "IBM Security Group with name '{}' created successfully".format(ibm_security_group.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_security_group)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_ibm_security_group", base=IBMBaseTask, bind=True)
def task_delete_ibm_security_group(self, task_id, cloud_id, region, security_group_id):
    """
    This request deletes a security group
    @return:
    """

    ibm_security_group = doosradb.session.query(IBMSecurityGroup).filter_by(id=security_group_id).first()
    if not ibm_security_group:
        return

    self.resource = ibm_security_group
    ibm_security_group.status = DELETING
    doosradb.session.commit()

    fetched_security_group = self.ibm_manager.rias_ops.fetch_ops.get_all_security_groups(
        name=ibm_security_group.name, vpc=ibm_security_group.ibm_vpc_network.name,
        required_relations=False
    )

    if fetched_security_group:
        self.ibm_manager.rias_ops.delete_security_group(fetched_security_group[0])

    ibm_security_group.status = DELETED
    doosradb.session.delete(ibm_security_group)
    doosradb.session.commit()
    LOGGER.info("Security Group '{name}' deleted successfully on IBM Cloud".format(name=ibm_security_group.name))


@celery.task(name="task_delete_ibm_security_group_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_security_group_workflow(self, task_id, cloud_id, region, security_group_id):
    """
    This request deletes a security group and detach the instance from it.
    @return:
    """
    workflow_steps = list()
    ibm_security_group = doosradb.session.query(IBMSecurityGroup).filter_by(id=security_group_id).first()
    if not ibm_security_group:
        return

    workflow_steps.append(task_detach_network_interface_from_security_group.si(task_id=task_id, cloud_id=cloud_id,
                                                                               region=region,
                                                                               security_group_id=security_group_id))

    workflow_steps.append(task_delete_ibm_security_group.si(task_id=task_id, cloud_id=cloud_id,
                                                            region=region, security_group_id=security_group_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_delete_ibm_security_group_rule", base=IBMBaseTask, bind=True)
def task_delete_ibm_security_group_rule(self, task_id, cloud_id, region, security_group_rule_id):
    """
    This request deletes a security group rule
    @return:
    """
    ibm_security_group_rule = doosradb.session.query(IBMSecurityGroupRule).filter_by(id=security_group_rule_id).first()
    if not ibm_security_group_rule:
        return

    self.resource = ibm_security_group_rule
    ibm_security_group_rule.status = DELETING
    doosradb.session.commit()

    fetched_obj = self.ibm_manager.rias_ops.fetch_ops.get_all_security_group_rules(
        security_group_id=ibm_security_group_rule.security_group.resource_id,
        direction=ibm_security_group_rule.direction,
        protocol=ibm_security_group_rule.protocol,
        code=ibm_security_group_rule.code,
        port_min=ibm_security_group_rule.port_min,
        port_max=ibm_security_group_rule.port_max,
        address=ibm_security_group_rule.address,
        cidr_block=ibm_security_group_rule.cidr_block,
        security_group_rule_id=ibm_security_group_rule.resource_id
    )

    if fetched_obj:
        self.ibm_manager.rias_ops.delete_security_group_rule(
            fetched_obj[0],
            security_group_id=ibm_security_group_rule.security_group.resource_id
        )

    ibm_security_group_rule.status = DELETED
    doosradb.session.delete(ibm_security_group_rule)
    doosradb.session.commit()
    LOGGER.info("Security Group Rule with '{id}' deleted successfully on IBM Cloud".format(
        id=ibm_security_group_rule.id))


@celery.task(name="task_detach_network_interface_from_security_group", base=IBMBaseTask, bind=True)
def task_detach_network_interface_from_security_group(self, task_id, cloud_id, region, security_group_id):
    """
    This request removes a network interface from a security group.
    @return:
    """

    ibm_security_group = doosradb.session.query(IBMSecurityGroup).filter_by(id=security_group_id).first()
    if not ibm_security_group:
        return

    self.resource = ibm_security_group

    fetched_obj = self.ibm_manager.rias_ops.fetch_ops.get_all_security_groups(name=ibm_security_group.name)

    if fetched_obj:
        for network_interface in ibm_security_group.network_interfaces:
            self.ibm_manager.rias_ops.detach_network_interface_from_security_group(
                fetched_obj[0], network_interface
            )

    ibm_security_group.network_interfaces = list()
    doosradb.session.commit()
    LOGGER.info("Network interface detached successfully from Security Group '{name}' on IBM Cloud".format(
        name=ibm_security_group.name))


@celery.task(name="task_delete_ibm_security_group_rule_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_security_group_rule_workflow(self, task_id, cloud_id, region, security_group_rule_id):
    """
    This request deletes a security group rule
    @return:
    """

    workflow_steps = list()

    ibm_security_group_rule = doosradb.session.query(IBMSecurityGroupRule).filter_by(id=security_group_rule_id).first()
    if not ibm_security_group_rule:
        return

    workflow_steps.append(task_delete_ibm_security_group_rule.si(task_id=task_id,
                                                                 cloud_id=cloud_id,
                                                                 region=region,
                                                                 security_group_rule_id=security_group_rule_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
