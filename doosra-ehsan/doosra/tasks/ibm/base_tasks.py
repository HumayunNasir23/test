import logging

from celery import Task
from sqlalchemy.orm.exc import DetachedInstanceError, StaleDataError

from doosra import db as doosradb
from doosra.common.clients.ibm_clients.exceptions import IBMExecuteError as ClientIBMExecuteError
from doosra.common.consts import CREATING, CREATED, DELETING, FAILED, ERROR_CREATING, ERROR_DELETING, SUCCESS, \
    UPDATING, COMPLETED
from doosra.ibm.common.consts import PROVISIONING, VALIDATION
from doosra.ibm.common.report_utils import ReportUtils
from doosra.ibm.managers import IBMManager
from doosra.ibm.managers.exceptions import (
    IBMAuthError,
    IBMConnectError,
    IBMExecuteError,
    IBMInvalidRequestError,
)
from doosra.migration.managers.exceptions import SLAuthError, SLExecuteError, SLInvalidRequestError, \
    SLRateLimitExceededError
from doosra.migration.data_migration.exceptions.exceptions import VolumeAttachmentException
from doosra.models import (
    IBMCloud,
    IBMTask,
    IBMSubTask,
    IBMVpcNetwork,
    IBMInstanceTasks, IBMInstance
)
from doosra.tasks.celery_app import app, celery
from doosra.tasks.exceptions import TaskFailureError, WorkflowTerminated

LOGGER = logging.getLogger("base_tasks.py")


class IBMBaseTask(Task):
    throws = (
        IBMAuthError,
        IBMConnectError,
        IBMExecuteError,
        IBMInvalidRequestError,
        SLInvalidRequestError,
        SLAuthError,
        SLExecuteError,
        SLRateLimitExceededError,
        TaskFailureError,
        WorkflowTerminated,
        VolumeAttachmentException,
    )
    ignore_result = True

    def __init__(self):
        self.cloud = None
        self.ibm_manager = None
        self.resource = None
        self.resource_name = None
        self.ibm_task = None
        self.region = None
        self.resource_type = None
        self.report_path = None
        self.vpn_cidr = None
        self.sub_task = None
        self.report_utils = ReportUtils()

    def __call__(self, *args, **kwargs):
        with app.app_context():
            try:
                LOGGER.info("Running '{0}'".format(self.name))
                self.region = kwargs["region"]
                self.cloud = doosradb.session.query(IBMCloud).filter_by(id=kwargs["cloud_id"]).first()
                if not self.cloud:
                    raise WorkflowTerminated(
                        "IBM Cloud with ID '{id}' not found".format(id=kwargs["cloud_id"]))

                self.ibm_task = doosradb.session.query(IBMTask).filter_by(id=kwargs["task_id"]).first()
                if not self.ibm_task:
                    raise WorkflowTerminated(
                        "IBM Task with ID '{id}' has failed".format(id=kwargs["task_id"]))

                self.ibm_manager = IBMManager(self.cloud, self.region)
                self.sub_task = IBMSubTask(task_id=self.request.id, resource_id=self.ibm_task.id)
                doosradb.session.add(self.sub_task)
                doosradb.session.commit()
                self.run(*args, **kwargs)
                self.sub_task.status = SUCCESS
                doosradb.session.commit()

            except StaleDataError:
                LOGGER.debug("SubTask for current task with ID '{id}' workflow removed".format(id=self.ibm_task.id))

            except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError, SLInvalidRequestError,
                    SLAuthError, SLExecuteError, SLRateLimitExceededError, TaskFailureError, WorkflowTerminated,
                    VolumeAttachmentException, ClientIBMExecuteError) as ex:

                if isinstance(ex, TaskFailureError):
                    LOGGER.error(ex)
                else:
                    LOGGER.info(ex)

                try:
                    if self.sub_task:
                        self.sub_task.status = FAILED
                        doosradb.session.commit()

                    if not self.ibm_task:
                        LOGGER.info("Task Failure: IBMTask with ID '{id}' not found".format(id=kwargs["task_id"]))
                        return

                    fail_message = ex
                    if isinstance(ex, TaskFailureError):
                        if self.resource_type == "dedicated_hosts":
                            LOGGER.info("IBM Workflow Task Terminated for ID: '{id}'".format(id=self.ibm_task.id))
                            self.ibm_task.status = FAILED
                            doosradb.session.merge(self.ibm_task)
                            doosradb.session.commit()
                            update_ibm_task(task_id=self.ibm_task.id)
                            self.request.chain = self.request.callbacks = None
                            return
                        fail_message = "Internal Server Error"

                    if self.resource:
                        self.report_utils.update_reporting(
                            task_id=self.ibm_task.id,
                            resource_name=self.vpn_cidr if self.vpn_cidr else self.resource.name,
                            resource_type=self.resource_type,
                            stage=PROVISIONING, status=FAILED, message=fail_message,
                            path=self.report_path if self.report_path else "")

                        if self.resource.status == DELETING:
                            self.resource.status = ERROR_DELETING

                        elif self.resource.status in [CREATING, UPDATING]:
                            self.resource.status = ERROR_CREATING

                        doosradb.session.merge(self.resource)
                        doosradb.session.commit()
                    else:
                        self.resource = doosradb.session.query(IBMVpcNetwork).filter_by(
                            id=self.ibm_task.resource_id).first()
                        if not self.resource:
                            self.resource = doosradb.session.query(IBMInstance).filter_by(
                                id=self.ibm_task.resource_id).first()
                        if not self.resource.status == CREATED:
                            self.resource.status = ERROR_CREATING
                            doosradb.session.commit()

                        if self.resource_name:
                            self.report_utils.update_reporting(
                                task_id=self.ibm_task.id,
                                resource_name=self.resource_name,
                                resource_type=self.resource_type,
                                stage=VALIDATION, status=FAILED, message=fail_message)

                    if kwargs.get("ibm_instance_task_id"):
                        ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
                            id=kwargs["ibm_instance_task_id"]).first()
                        if ibm_instance_task:
                            ibm_instance_task.status = FAILED
                            ibm_instance_task.in_focus = False
                            doosradb.session.commit()

                    if hasattr(ex, 'trace_id'):
                        self.ibm_task.trace_id = ex.trace_id
                        doosradb.session.commit()

                    if not isinstance(ex, WorkflowTerminated):
                        self.ibm_task.message = str(ex)
                        doosradb.session.commit()
                        return

                    LOGGER.info("IBM Workflow Task Terminated for ID: '{id}'".format(id=self.ibm_task.id))
                    self.ibm_task.status = FAILED
                    doosradb.session.merge(self.ibm_task)
                    doosradb.session.commit()
                    update_ibm_task(task_id=self.ibm_task.id)
                    self.request.chain = self.request.callbacks = None

                except DetachedInstanceError as e:
                    LOGGER.info("Instance detached error occurred but this can be ignored \n {}".format(str(e)))

    def on_failure(self, exc, task_id, args, kwargs, info):
        """
        This is run by the worker when the task fails.
        :return:
        """
        with app.app_context():
            LOGGER.error('{0!r} failed: {1!r}'.format(task_id, exc))
            if self.sub_task:
                self.sub_task.status = FAILED
                doosradb.session.commit()

            ibm_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
            if ibm_task:
                ibm_task.status = FAILED
                doosradb.session.commit()
                update_ibm_task(task_id=ibm_task.id)
                self.report_utils.stop_reporting(task_id=ibm_task.id, message=exc)

            if self.resource:
                if self.resource.status == DELETING:
                    self.resource.status = ERROR_DELETING

                elif self.resource.status in [CREATING, UPDATING]:
                    self.resource.status = ERROR_CREATING
            doosradb.session.commit()


@celery.task(name="update_ibm_task", bind=True)
def update_ibm_task(self, task_id):
    """Update IBMTask status to success if all tasks of current workflow are finished"""
    ibm_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    tasks = doosradb.session.query(IBMSubTask).filter_by(resource_id=task_id).all()
    status = SUCCESS
    while tasks:
        i = 0
        while i < len(tasks):
            if tasks[i].status in [SUCCESS, FAILED]:
                if tasks[i].status == FAILED:
                    status = FAILED
                doosradb.session.delete(tasks[i])
                del tasks[i]
            i += 1
        doosradb.session.commit()
        tasks = doosradb.session.query(IBMSubTask).filter_by(resource_id=task_id).all()

    ibm_task.status = status

    if status in {SUCCESS, FAILED}:
        vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=ibm_task.resource_id).first()
        if vpc:
            workspace = vpc.workspace
            if workspace:
                workspace.status = COMPLETED
    doosradb.session.commit()

    if ibm_task.status == FAILED:
        return

    LOGGER.info("IBM task with ID '{id}' updated successfully".format(id=ibm_task.id))


@celery.task(name="update_group_tasks", base=IBMBaseTask, bind=True)
def update_group_tasks(self, task_id, cloud_id, region, message):
    """
    This method is called after all the other tasks in a group have finished their execution
    :return:
    """
    tasks = doosradb.session.query(IBMSubTask).filter_by(resource_id=task_id).all()
    for task in tasks:
        if task.status == FAILED:
            raise WorkflowTerminated("IBM Task failed for group {message}".format(message=message))

    return message
