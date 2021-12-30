"""
Celery tasks for IBM Dedicated Hosts
"""
import logging

from doosra import db as doosradb
from doosra.common.consts import FAILED, SUCCESS
from doosra.common.consts import CREATED, CREATING, IN_PROGRESS, FAILED, SUCCESS
from doosra.ibm.common.consts import PROVISIONING, VALIDATION
from doosra.ibm.managers.exceptions import IBMInvalidRequestError
from doosra.models import IBMTask, WorkSpace, IBMDedicatedHost
from doosra.tasks.celery_app import celery
from doosra.tasks.exceptions import TaskFailureError
from doosra.tasks.ibm.base_tasks import IBMBaseTask

LOGGER = logging.getLogger(__name__)


@celery.task(name="validate_dedicated_host", base=IBMBaseTask, bind=True)
def task_validate_dedicated_host(self, task_id, cloud_id, region, data):
    """
    Celery task to validate an IBM Dedicated Host
    :param self:
    :param ibm_task_id: <string> ID of the associate IBMTask
    :param data: <dict> FE JSON for the Dedicated Host
    :return:
    """

    from doosra.common.clients.ibm_clients import DedicatedHostsClient

    self.resource_type = "dedicated_hosts"
    self.resource_name = data["name"]
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )

    dh_client = DedicatedHostsClient(cloud_id=data["cloud_id"])
    dedicated_hosts = dh_client.list_dedicated_hosts(region=data["region"])
    for dh in dedicated_hosts:
        if data["name"] == dh["name"]:
            self.report_utils.update_reporting(
                task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
                status=FAILED
            )
            raise IBMInvalidRequestError(
                "IBM Dedicated Host '{name}' already Provisioned in {region}".format(name=data["name"],
                                                                                     region=data["region"]))

    LOGGER.info("IBM Dedicated Host '{name}' in {region} VALIDATED Successfully..!".format(name=data["name"],
                                                                                           region=data["region"]))
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )


@celery.task(name="create_dedicated_host")
def task_create_dedicated_host(ibm_task_id, data):
    """
    Celery task to create an IBM Dedicated Host
    :param ibm_task_id: <string> ID of the associate IBMTask
    :param data: <dict> FE JSON for the Dedicated Host
    :return:
    """
    from doosra.ibm.dedicated_hosts.utils import configure_dedicated_host

    try:
        ibm_dedicated_host = configure_dedicated_host(data)

        task = doosradb.session.query(IBMTask).filter_by(id=ibm_task_id).first()
        task.resource_id = ibm_dedicated_host.id
        task.status = SUCCESS
    except TaskFailureError as ex:
        task = doosradb.session.query(IBMTask).filter_by(id=ibm_task_id).first()
        task.message = str(ex)
        task.status = FAILED

    doosradb.session.commit()


@celery.task(name="create_dedicated_host_workflow", base=IBMBaseTask, bind=True)
def task_create_dedicated_host_workflow(self, task_id, cloud_id, region, data, workspace_id):
    """
    Celery task to create an IBM Dedicated Host
    :param ibm_task_id: <string> ID of the associate IBMTask
    :param data: <dict> FE JSON for the Dedicated Host
    :return:
    """
    from doosra.ibm.dedicated_hosts.utils import configure_dedicated_host

    LOGGER.info(f"Creating Dedicated Host {data['name']} for cloud {cloud_id} in region {region}")
    self.resource_type = "dedicated_hosts"
    self.resource_name = data["name"]

    data_copy = data.copy()

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    try:
        configured_dedicated_host = configure_dedicated_host(data, workspace_id=workspace_id)
        self.report_utils.update_reporting(
            task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=PROVISIONING,
            status=SUCCESS
        )
        workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
        if not workspace:
            raise

        new_req_metadata = workspace.request_metadata
        instances_list = []
        for instance_ in new_req_metadata["instances"]:
            if instance_.get("dedicated_host_name") == configured_dedicated_host.name and region == configured_dedicated_host.region:
                instance_["dedicated_host_id"] = configured_dedicated_host.id
            instances_list.append(instance_)
        new_req_metadata["instances"] = instances_list
        workspace.request_metadata = new_req_metadata
        doosradb.session.commit()

    except TaskFailureError as ex:
        LOGGER.error(ex)
        self.report_utils.update_reporting(
            task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=PROVISIONING,
            status=FAILED, message=str(ex)
        )
        if not workspace_id:
            raise

        workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
        if not workspace:
            raise

        new_req_metadata = workspace.request_metadata.copy()
        if "dedicated_hosts" not in new_req_metadata:
            new_req_metadata["dedicated_hosts"] = []

        new_req_metadata["dedicated_hosts"].append(data_copy)

        # Stupid necessary thing, do not remove
        workspace.request_metadata = {}
        doosradb.session.commit()
        ###

        workspace.request_metadata = new_req_metadata.copy()
        doosradb.session.commit()
        raise


@celery.task(name="delete_dedicated_host")
def task_delete_dedicated_host(ibm_task_id, cloud_id, dedicated_host_id):
    """
    Celery task to delete an IBM Dedicated Host
    :param ibm_task_id: <string> ID of the associate IBMTask
    :param cloud_id: <string> ID of the cloud in doosradb
    :param dedicated_host_id: <string> ID of the Dedicated Host in doosradb
    :return:
    """
    from doosra.ibm.dedicated_hosts.utils import delete_dedicated_host

    status = SUCCESS
    message = None
    try:
        delete_dedicated_host(cloud_id=cloud_id, dedicated_host_id=dedicated_host_id)
    except TaskFailureError as ex:
        status = FAILED
        message = str(ex)

    task = doosradb.session.query(IBMTask).filter_by(id=ibm_task_id).first()
    task.status = status
    task.message = message
    doosradb.session.commit()


@celery.task(name="create_dedicated_host_group")
def task_create_dedicated_host_group(ibm_task_id, data):
    """
    Celery task to create an IBM Dedicated Host Group
    :param ibm_task_id: <string> ID of the associate IBMTask
    :param data: <dict> FE JSON for the Dedicated Host Group
    :return:
    """
    from doosra.ibm.dedicated_hosts.utils import configure_dedicated_host_group

    try:
        ibm_dedicated_host_group = configure_dedicated_host_group(data)

        task = doosradb.session.query(IBMTask).filter_by(id=ibm_task_id).first()
        task.resource_id = ibm_dedicated_host_group.id
        task.status = SUCCESS
    except TaskFailureError as ex:
        task = doosradb.session.query(IBMTask).filter_by(id=ibm_task_id).first()
        task.message = str(ex)
        task.status = FAILED

    doosradb.session.commit()


@celery.task(name="delete_dedicated_host_group")
def task_delete_dedicated_host_group(ibm_task_id, cloud_id, dedicated_host_group_id):
    """
    Celery task to delete an IBM Dedicated Host Group
    :param ibm_task_id: <string> ID of the associate IBMTask
    :param cloud_id: <string> ID of the cloud in doosradb
    :param dedicated_host_group_id: <string> ID of the Dedicated Host Group in doosradb
    :return:
    """
    from doosra.ibm.dedicated_hosts.utils import delete_dedicated_host_group

    status = SUCCESS
    message = None
    try:
        delete_dedicated_host_group(cloud_id=cloud_id, dedicated_host_group_id=dedicated_host_group_id)
    except TaskFailureError as ex:
        status = FAILED
        message = str(ex)

    task = doosradb.session.query(IBMTask).filter_by(id=ibm_task_id).first()
    task.status = status
    task.message = message
    doosradb.session.commit()


@celery.task(name="sync_dedicated_host_profiles")
def task_sync_dedicated_host_profiles(ibm_task_id, cloud_id, region):
    """
    Celery task to sync all Dedicated Host profiles with IBM and store them in DB
    :param ibm_task_id: <string> ID of the associate IBMTask
    :param cloud_id: <string> ID of the cloud in doosradb
    :param region: <string> Region of the IBM Cloud
    :return:
    """
    from doosra.ibm.dedicated_hosts.utils import sync_dedicated_host_profiles

    status = SUCCESS
    message = None
    try:
        sync_dedicated_host_profiles(cloud_id=cloud_id, region=region)
    except TaskFailureError as ex:
        status = FAILED
        message = str(ex)
        LOGGER.error(f"Profiles sync for cloud {cloud_id} region {region} failed because: {message}")

    task = doosradb.session.query(IBMTask).filter_by(id=ibm_task_id).first()
    if not task:
        LOGGER.debug(f"No IBM Task found with ID {ibm_task_id}")
        return

    task.status = status
    task.message = message
    doosradb.session.commit()
