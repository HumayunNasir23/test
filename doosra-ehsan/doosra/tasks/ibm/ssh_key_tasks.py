import logging

from celery import chain

from doosra import db as doosradb
from doosra.common.consts import CREATED, CREATING, IN_PROGRESS, FAILED, SUCCESS
from doosra.common.utils import DELETING, DELETED
from doosra.ibm.common.billing_utils import log_resource_billing, IBMResourceGroup
from doosra.ibm.common.consts import PROVISIONING, VALIDATION
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.ibm.managers.exceptions import (
    IBMInvalidRequestError,
)
from doosra.models import (
    IBMSshKey,
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("ssh_key_tasks.py")


@celery.task(name="validate_ibm_ssh_key", base=IBMBaseTask, bind=True)
def task_validate_ibm_ssh_key(self, task_id, cloud_id, region, ssh_key):
    """Check if ssh key already exists"""

    self.resource_name = ssh_key["name"]
    self.resource_type = 'ssh_keys'
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    existing_ssh_keys = self.ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys()

    for existing_ssh_key in existing_ssh_keys:
        if existing_ssh_key.name == ssh_key["name"] and existing_ssh_key.public_key != ssh_key["public_key"]:
            raise IBMInvalidRequestError(
                "IBM SSH Key with name '{}' already configured on IBM with a different public key.".format(
                    ssh_key["name"]
                )
            )
        elif existing_ssh_key.public_key == ssh_key["public_key"] and existing_ssh_key.name != ssh_key["name"]:
            raise IBMInvalidRequestError(
                "IBM SSH Key with public key '{}' already configured with a different name '{}'.".format(
                    ssh_key["name"], existing_ssh_key.name, ssh_key["name"], existing_ssh_key.name
                )
            )

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info("IBM SSH key with name '{}' validated successfully".format(ssh_key["name"]))


@celery.task(name="add_ibm_ssh_key", base=IBMBaseTask, bind=True)
def task_create_ibm_ssh_key(self, task_id, cloud_id, region, ssh_key_id, resource_group=None):
    """Create and configure ssh key"""

    ibm_ssh_key = doosradb.session.query(IBMSshKey).filter_by(id=ssh_key_id).first()
    if not ibm_ssh_key:
        return

    self.resource = ibm_ssh_key
    self.resource_type = "ssh_keys"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_ssh_key = self.ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(
        name=ibm_ssh_key.name, public_key=ibm_ssh_key.public_key
    )

    configured_ssh_key = configured_ssh_key[0] if configured_ssh_key else None
    if not configured_ssh_key:
        ibm_ssh_key.status = CREATING
        if resource_group:
            ibm_resource_group = IBMResourceGroup(name=resource_group, cloud_id=cloud_id)
            ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
            ibm_ssh_key.ibm_resource_group = ibm_resource_group

        doosradb.session.commit()
        self.resource = ibm_ssh_key
        configured_ssh_key = configure_and_save_obj_confs(self.ibm_manager, ibm_ssh_key)

    ibm_ssh_key.status = CREATED
    ibm_ssh_key.resource_id = configured_ssh_key.resource_id
    doosradb.session.commit()
    LOGGER.info(
        "IBM SSH Key with name '{}' created successfully".format(ibm_ssh_key.name)
    )

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_ssh_key)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_ssh_key", base=IBMBaseTask, bind=True)
def task_delete_ssh_key(self, task_id, cloud_id, region, ssh_key_id):
    """
    This request deletes a ssh key from IBM cloud
    @return:
    """

    ibm_ssh_key = doosradb.session.query(IBMSshKey).filter_by(id=ssh_key_id).first()
    if not ibm_ssh_key:
        return

    self.resource = ibm_ssh_key
    ibm_ssh_key.status = DELETING
    doosradb.session.commit()

    fetched_ssh_key = self.ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(
        name=ibm_ssh_key.name,
        required_relations=False
    )

    if fetched_ssh_key:
        self.ibm_manager.rias_ops.delete_ssh_key(fetched_ssh_key[0])

    ibm_ssh_key.status = DELETED
    doosradb.session.delete(ibm_ssh_key)
    doosradb.session.commit()
    LOGGER.info("IBM ssh key '{name}' deleted successfully on IBM Cloud".format(name=ibm_ssh_key.name))


@celery.task(name="task_delete_ssh_key_workflow", base=IBMBaseTask, bind=True)
def task_delete_ssh_key_workflow(self, task_id, cloud_id, region, ssh_key_id):
    """
    This request is workflow for the deletion for ssh key
    @return:
    """

    workflow_steps = list()

    ibm_ssh_key = doosradb.session.query(IBMSshKey).filter_by(id=ssh_key_id).first()
    if not ibm_ssh_key:
        return

    workflow_steps.append(task_delete_ssh_key.si(task_id=task_id, cloud_id=cloud_id,
                                                 region=region, ssh_key_id=ssh_key_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
