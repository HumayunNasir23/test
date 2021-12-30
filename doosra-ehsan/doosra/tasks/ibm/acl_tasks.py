import logging

from celery import chain

from doosra import db as doosradb
from doosra.common.consts import IN_PROGRESS, FAILED, SUCCESS

from doosra.ibm.common.billing_utils import log_resource_billing, IBMResourceGroup
from doosra.ibm.common.consts import PROVISIONING, VALIDATION
from doosra.common.utils import CREATED, DELETING, DELETED, CREATING
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.ibm.managers.exceptions import (
    IBMInvalidRequestError,
)
from doosra.models import (
    IBMNetworkAcl,
    IBMNetworkAclRule)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("acl_tasks.py")


@celery.task(name="validate_ibm_acl", base=IBMBaseTask, bind=True)
def task_validate_ibm_acl(self, task_id, cloud_id, region, vpc_name, acl):
    """Check if ACL already exists"""
    self.resource_name = acl["name"]
    self.resource_type = "acls"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    existing_acl = self.ibm_manager.rias_ops.fetch_ops.get_all_networks_acls(name=acl["name"])
    if existing_acl:
        raise IBMInvalidRequestError("IBM ACL with name '{acl}' already configured".format(acl=acl["name"]))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info("IBM ACL with name '{acl}' validated successfully".format(acl=acl["name"]))


@celery.task(name="create_ibm_acl", base=IBMBaseTask, bind=True)
def task_create_ibm_acl(self, task_id, cloud_id, region, acl_id, resource_group=None):
    """Create and configure ACL"""
    ibm_acl = doosradb.session.query(IBMNetworkAcl).filter_by(id=acl_id).first()
    if not ibm_acl:
        return
    ibm_acl.status = CREATING

    if resource_group:
        ibm_resource_group = IBMResourceGroup(name=resource_group, cloud_id=cloud_id)
        ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
        ibm_acl.ibm_resource_group = ibm_resource_group

    doosradb.session.commit()
    self.resource = ibm_acl
    self.resource_type = "acls"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_acl = configure_and_save_obj_confs(self.ibm_manager, ibm_acl)
    ibm_acl.status = CREATED
    ibm_acl.resource_id = configured_acl.resource_id
    doosradb.session.commit()
    LOGGER.info("IBM ACL with name '{acl}' created successfully".format(acl=ibm_acl.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_acl)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_ibm_network_acl", base=IBMBaseTask, bind=True)
def task_delete_network_acl(self, task_id, cloud_id, region, ibm_network_acl_id):
    """
    This request deletes a network acl
    @return:
    """
    ibm_network_acl = doosradb.session.query(IBMNetworkAcl).filter_by(id=ibm_network_acl_id).first()
    if not ibm_network_acl:
        return

    self.resource = ibm_network_acl
    ibm_network_acl.status = DELETING
    doosradb.session.commit()

    fetched_acl = self.ibm_manager.rias_ops.fetch_ops.get_all_networks_acls(
        name=ibm_network_acl.name, vpc=ibm_network_acl.ibm_vpc_network.name)

    if fetched_acl:
        self.ibm_manager.rias_ops.delete_network_acl(fetched_acl[0])

    ibm_network_acl.status = DELETED
    doosradb.session.delete(ibm_network_acl)
    doosradb.session.commit()
    LOGGER.info("Network ACL '{name}' deleted successfully on IBM Cloud".format(name=ibm_network_acl.name))


@celery.task(name="task_delete_ibm_network_acl_rule", base=IBMBaseTask, bind=True)
def task_delete_network_acl_rule(self, task_id, cloud_id, region, ibm_network_acl_rule_id):
    """
    This request deletes a network ACL Rule.
    @return:
    """

    ibm_network_acl_rule = doosradb.session.query(IBMNetworkAclRule).filter_by(id=ibm_network_acl_rule_id).first()
    if not ibm_network_acl_rule:
        return

    self.resource = ibm_network_acl_rule
    ibm_network_acl_rule.status = DELETING
    doosradb.session.commit()

    fetched_acl_rule = self.ibm_manager.rias_ops.fetch_ops.get_all_network_acl_rules(
        acl_id=ibm_network_acl_rule.ibm_network_acl.resource_id,
        name=ibm_network_acl_rule.name
    )

    if fetched_acl_rule:
        self.ibm_manager.rias_ops.delete_network_acl_rule(
            fetched_acl_rule[0],
            acl_id=ibm_network_acl_rule.ibm_network_acl.resource_id
        )

    ibm_network_acl_rule.status = DELETED
    doosradb.session.delete(ibm_network_acl_rule)
    doosradb.session.commit()
    LOGGER.info("Network ACL Rule '{name}' deleted successfully on IBM Cloud".format(name=ibm_network_acl_rule.name))


@celery.task(name="task_delete_network_acl_workflow", base=IBMBaseTask, bind=True)
def task_delete_network_acl_workflow(self, task_id, cloud_id, region, ibm_network_acl_id):
    """
    This request is a workflow for acl deletion
    @return:
    """
    workflow_steps = list()

    ibm_network_acl = doosradb.session.query(IBMNetworkAcl).filter_by(id=ibm_network_acl_id).first()
    if not ibm_network_acl:
        return

    workflow_steps.append(task_delete_network_acl.si(task_id=task_id, cloud_id=cloud_id,
                                                     region=region, ibm_network_acl_id=ibm_network_acl_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_delete_network_acl_rule_workflow", base=IBMBaseTask, bind=True)
def task_delete_network_acl_rule_workflow(self, task_id, cloud_id, region, ibm_network_acl_rule_id):
    """
    This request is a workflow for acl rule deletion
    @return:
    """
    workflow_steps = list()

    ibm_network_acl_rule = doosradb.session.query(IBMNetworkAclRule).filter_by(id=ibm_network_acl_rule_id).first()
    if not ibm_network_acl_rule:
        return

    workflow_steps.append(task_delete_network_acl_rule.si(task_id=task_id, cloud_id=cloud_id,
                                                          region=region,
                                                          ibm_network_acl_rule_id=ibm_network_acl_rule_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
