"""
This file hosts models for generic tasks tied to resources which run the whole flow
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, JSON, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, deferred, relationship

from doosra import db

workflow_tree_mappings = db.Table(
    'workflow_tree_mappings',
    Column("task_id", String(32), ForeignKey("workflow_tasks.id"), nullable=False),
    Column("next_task_id", String(32), ForeignKey("workflow_tasks.id"), nullable=False),
)


class WorkflowRoot(db.Model):
    """
    This database model holds the information for the root of the workflow tree
    """
    __tablename__ = 'workflow_roots'

    ID_KEY = "id"
    STATUS_KEY = "status"
    ASSOCIATED_TASKS_KEY = "associated_tasks"
    WORKFLOW_NAME_KEY = "workflow_name"
    WORKFLOW_NATURE_KEY = "workflow_nature"
    FE_REQUEST_DATA_KEY = "fe_request_data"
    CREATED_AT_KEY = "created_at"
    COMPLETED_AT_KEY = "completed_at"

    # This is the status of a CALLBACK ROOT when it is CREATED
    STATUS_ON_HOLD = "ON_HOLD"
    # This is the initial status of the ROOT when it is CREATED
    STATUS_PENDING = "PENDING"
    # The task has been initiated, but is not yet picked up by any worker
    STATUS_INITIATED = "INITIATED"
    # At least one of the tasks in this tree is running
    STATUS_RUNNING = "RUNNING"
    # All of the tasks in the tree were successful
    STATUS_C_SUCCESSFULLY = "COMPLETED_SUCCESSFULLY"
    # All of the tasks in the tree were successful and the root itself is complete but is waiting for status holding
    #  callbacks to finish (WFC = Waiting for Callbacks)
    STATUS_C_SUCCESSFULLY_WFC = "COMPLETED_SUCCESSFULLY_WFC"
    # One or more of the tasks in the tree failed
    STATUS_C_W_FAILURE = "COMPLETED_WITH_FAILURE"
    # One or more of the tasks in the tree failed and the root itself is complete but is waiting for status holding
    #  callacks to finish (WFC = Waiting for Callbacks)
    STATUS_C_W_FAILURE_WFC = "COMPLETED_WITH_FAILURE_WFC"

    ROOT_TYPE_NORMAL = "NORMAL"
    ROOT_TYPE_ON_SUCCESS = "ON_SUCCESS"
    ROOT_TYPE_ON_FAILURE = "ON_FAILURE"
    ROOT_TYPE_ON_COMPLETE = "ON_COMPLETE"
    id = Column(String(32), primary_key=True)
    # DO NOT ACCESS STATUS DIRECTLY
    __status = Column(
        "status",
        Enum(
            STATUS_ON_HOLD,
            STATUS_PENDING,
            STATUS_INITIATED,
            STATUS_RUNNING,
            STATUS_C_SUCCESSFULLY_WFC,
            STATUS_C_SUCCESSFULLY,
            STATUS_C_W_FAILURE_WFC,
            STATUS_C_W_FAILURE
        ),
        default=STATUS_PENDING,
        nullable=False
    )
    # Any custom name that you would want to give to a task
    workflow_name = Column(String(128))
    root_type = Column(
        Enum(ROOT_TYPE_NORMAL, ROOT_TYPE_ON_SUCCESS, ROOT_TYPE_ON_FAILURE, ROOT_TYPE_ON_COMPLETE),
        default=ROOT_TYPE_NORMAL
    )
    # What is the overall tree doing? CREATE/DELETE/UPDATE
    workflow_nature = Column(String(128))
    # If the root was initiated from an API, store the request data in this column
    fe_request_data = deferred(Column(JSON))
    # This is internal to the Workflow Controller logic, lets forget about this for now
    executor_running = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())
    # The difference shows time it took for this task to be initiated by workflow_manger
    initiated_at = Column(DateTime)
    # The difference shows time it took for the first task to be initiated by workflow executor
    started_at = Column(DateTime)
    # The difference shows time it took for the whole tree to execute
    completed_at = Column(DateTime)
    project_id = Column(String(32), nullable=False)
    # to_json() of the parent root at the time its callback task was initiated
    __parent_root_copy = deferred(Column('parent_root_copy', JSON))
    # Whether or not the parent root should update its status to COMPLETED_SUCCESSFULY/COMPLETED_WITH_FAILURE before
    #  this task is completed
    hold_parent_status_update = Column(Boolean, default=False)

    parent_root_id = Column(String(32), ForeignKey('workflow_roots.id'))

    associated_tasks = relationship('WorkflowTask', backref="root", cascade="all, delete-orphan", lazy='dynamic')
    # DO NOT append directly to this relation. Use add_callback_root func
    callback_roots = relationship('WorkflowRoot', backref=backref("parent_root", remote_side=[id]), lazy='dynamic')

    def __init__(
            self, workflow_name=None, workflow_nature=None, fe_request_data=None, project_id=None,
            root_type=ROOT_TYPE_NORMAL
    ):
        self.id = str(uuid.uuid4().hex)
        self.created_at = datetime.utcnow()
        self.root_type = root_type or self.ROOT_TYPE_NORMAL
        if self.root_type != self.ROOT_TYPE_NORMAL:
            self.status = self.STATUS_ON_HOLD
        self.workflow_name = workflow_name
        self.workflow_nature = workflow_nature
        self.fe_request_data = fe_request_data
        self.project_id = project_id

    def add_next_task(self, next_task):
        """
        Add a task to the first group of tasks for the workflow
        :param next_task:
        :return:
        """
        assert isinstance(next_task, WorkflowTask)
        self.associated_tasks.append(next_task)

    def add_callback_root(self, callback_root, hold_parent_status_update=False):
        """
        Add a callback workflow for the root
        :param callback_root: <Object: WorkflowRoot> The callback root
        :param hold_parent_status_update: <bool> Whether or not the parent should wait for the callback task to complete
                                          before updating its status
        :return:
        """
        assert self.root_type == self.ROOT_TYPE_NORMAL
        assert callback_root.root_type in [
            self.ROOT_TYPE_ON_SUCCESS, self.ROOT_TYPE_ON_FAILURE, self.ROOT_TYPE_ON_COMPLETE
        ]
        callback_root.hold_parent_status_update = hold_parent_status_update
        self.callback_roots.append(callback_root)

    @property
    def parent_root_copy(self):
        return self.__parent_root_copy

    def __generate_parent_root_copy(self):
        self.__parent_root_copy = self.parent_root.to_json()

    @property
    def status_holding_callbacks_count(self):
        """
        Returns the number of callback roots that will block the status update to COMPLETED_SUCCESSFULLY or
        COMPLETED_WITH_FAILURE
        :return: <int> number of status holding callbacks
        """
        if self.root_type != WorkflowRoot.ROOT_TYPE_NORMAL:
            return 0

        return self.callback_roots.filter(
            WorkflowRoot.hold_parent_status_update,
            WorkflowRoot.status.in_(
                {
                    WorkflowRoot.STATUS_ON_HOLD,
                    WorkflowRoot.STATUS_PENDING,
                    WorkflowRoot.STATUS_INITIATED,
                    WorkflowRoot.STATUS_RUNNING
                }
            )
        ).count()

    @hybrid_property
    def status(self):
        """
        Hybrid property (you can query on this) for status getter
        :return:
        """
        return self.__status

    @status.setter
    def status(self, new_status):
        """
        Hybrid property (you can query on this) for status setter
        :param new_status: <string> status to be set
        """
        if new_status == self.STATUS_PENDING:
            if self.status == self.STATUS_ON_HOLD and self.root_type in [
                self.ROOT_TYPE_ON_SUCCESS, self.ROOT_TYPE_ON_FAILURE, self.ROOT_TYPE_ON_COMPLETE
            ]:
                self.__generate_parent_root_copy()
            self.created_at = datetime.utcnow()
        elif new_status == self.STATUS_INITIATED:
            self.initiated_at = datetime.utcnow()
        elif new_status == self.STATUS_RUNNING:
            self.started_at = datetime.utcnow()
        elif new_status in [
            self.STATUS_C_SUCCESSFULLY_WFC, self.STATUS_C_SUCCESSFULLY, self.STATUS_C_W_FAILURE_WFC,
            self.STATUS_C_W_FAILURE
        ]:
            self.completed_at = datetime.utcnow()

        self.__status = new_status

    @property
    def next_tasks(self):
        """
        Property to get next (first group) tasks of the root task
        :return:
        """
        return self.associated_tasks.filter(~WorkflowTask._previous_tasks.any()).all()

    @property
    def in_focus_tasks(self):
        """
        Property to get tasks which are in focus right now (running, failed, completed but not acknowledged, failed but
        not acknowledged)
        :return:
        """
        return self.associated_tasks.filter(WorkflowTask.in_focus).all()

    def to_json(self, metadata=False):
        resp = {
            self.ID_KEY: self.id,
            self.WORKFLOW_NAME_KEY: self.workflow_name,
            self.WORKFLOW_NATURE_KEY: self.workflow_nature,
            self.FE_REQUEST_DATA_KEY: self.fe_request_data,
            self.STATUS_KEY: self.status,
            self.CREATED_AT_KEY: str(self.created_at) if self.created_at else None,
            self.COMPLETED_AT_KEY: str(self.completed_at) if self.completed_at else None
        }

        if not metadata:
            resp[self.ASSOCIATED_TASKS_KEY] = [task.to_json() for task in self.associated_tasks]

        return resp


class WorkflowTask(db.Model):
    """
    This database model holds information for a task that is tied to a resource
    """
    __tablename__ = 'workflow_tasks'

    ID_KEY = "id"
    STATUS_KEY = "status"
    RESOURCE_ID_KEY = "resource_id"
    RESOURCE_TYPE_KEY = "resource_type"
    TASK_TYPE_KEY = "task_type"
    TASK_METADATA_KEY = "task_metadata"
    MESSAGE_KEY = "message"
    IN_FOCUS_KEY = "in_focus"
    PREVIOUS_TASK_IDS_KEY = "previous_task_ids"
    NEXT_TASK_IDS_KEY = "next_task_ids"

    # When the task is created but not initated yet
    STATUS_PENDING = "PENDING"
    # When the task is initiated, but not picked up by any worker yet
    STATUS_INITIATED = "INITIATED"
    # When the task is executing, IN FOCUS
    STATUS_RUNNING = "RUNNING"
    # When the task needs to wait for something before declaring it successful/failed, IN FOCUS
    STATUS_RUNNING_WAIT = "RUNNING_WAIT"
    # Internal, same as RUNNING_WAIT, IN FOCUS
    STATUS_RUNNING_WAIT_INITIATED = "RUNNING_WAIT_INITIATED"
    # When the task is completed succesfully, IN FOCUS but is set to False when the executor runs again
    STATUS_SUCCESSFUL = "SUCCESSFUL"
    # When the task fails, IN FOCUS
    STATUS_FAILED = "FAILED"

    TYPE_ATTACH = "ATTACH"
    TYPE_DETACH = "DETACH"
    TYPE_VALIDATE = "VALIDATE"
    TYPE_CREATE = "CREATE"
    TYPE_DELETE = "DELETE"
    TYPE_DISCOVERY = "DISCOVERY"
    TYPE_UPDATE = "UPDATE"
    TYPE_RESTORE = "RESTORE"
    TYPE_MAP = "MAP"
    TYPE_BACKUP = "BACKUP"
    TYPE_DELETE_BACKUP = "DELETE_BACKUP"
    TYPE_DELETE_PLAN = "DELETE_PLAN"
    TYPE_TRANSLATE = "TRANSLATE"
    TYPE_EXECUTE_RESTORE = "EXECUTE_RESTORE"
    TYPE_EXECUTE_BACKUP = "EXECUTE_BACKUP"
    TYPE_CONSUMPTION = "CONSUMPTION"
    TYPE_DELETE_CONSUMPTION = "DELETE_BACKUP_CONSUMPTION"
    TYPE_ENABLE = "ENABLE"
    TYPE_DISABLE = "DISABLE"

    id = Column(String(32), primary_key=True)
    # Id of the resource the task belongs to. Can be none if it does not belong to any resource
    resource_id = Column(String(32))
    # Type of the resource (or DB Model Name) of the resource of the task it belongs to
    resource_type = Column(String(512), nullable=False)
    task_type = Column(String(512), nullable=False)

    # Store any information regarding the task, grey area to store whatever you like, rough work section
    task_metadata = deferred(Column(JSON))
    # DO NOT ACCESS STATUS DIRECTLY
    __status = Column(
        "status",
        Enum(
            STATUS_PENDING, STATUS_INITIATED, STATUS_RUNNING, STATUS_RUNNING_WAIT, STATUS_RUNNING_WAIT_INITIATED,
            STATUS_SUCCESSFUL, STATUS_FAILED
        ),
        default=STATUS_PENDING,
        nullable=False
    )
    # This column can store any messages that relate to the failure of a task
    message = Column(String(1024))
    # in_focus should only be changed in the workflow_tasks file. DO NOT CHANGE IT ANYWHERE ELSE
    in_focus = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())
    # The difference shows time it took for this task to be initiated by workflow executor
    initiated_at = Column(DateTime)
    # The difference shows time it took for the task to be picked up by a worker
    started_at = Column(DateTime)
    # The difference shows time it took for the task to complete execution
    completed_at = Column(DateTime)

    _next_tasks = relationship(
        'WorkflowTask',
        secondary=workflow_tree_mappings,
        primaryjoin=id == workflow_tree_mappings.c.task_id,
        secondaryjoin=id == workflow_tree_mappings.c.next_task_id,
        backref=backref('_previous_tasks', lazy='dynamic'),
        lazy='dynamic'
    )

    root_id = Column(String(32), ForeignKey('workflow_roots.id'), nullable=False)

    def __init__(self, task_type, resource_type, resource_id=None, task_metadata=None):
        self.id = str(uuid.uuid4().hex)
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.task_type = task_type
        self.task_metadata = task_metadata
        self.created_at = datetime.utcnow()

    def add_next_task(self, next_task):
        """
        Add subsequent task
        :param next_task: <object of WorkflowTask> Task that should run if this task is successful
        """
        assert isinstance(next_task, WorkflowTask)
        if not self.root:
            raise ValueError("Invalid operation add_next_task, {} does not have root".format(self.id))

        next_task.root = self.root
        self._next_tasks.append(next_task)

    def add_previous_task(self, previous_task):
        """
        Add pre-req task
        :param previous_task: <object of WorkflowTask> Task which should be successful for this task to run
        """
        assert isinstance(previous_task, WorkflowTask)
        if not self.root:
            raise ValueError("Invalid operation add_previous_task, {} does not have root".format(self.id))

        previous_task.root = self.root
        self._previous_tasks.append(previous_task)

    @hybrid_property
    def status(self):
        """
        Hybrid property (you can query on this) for status getter
        :return:
        """
        return self.__status

    @status.setter
    def status(self, new_status):
        """
        Hybrid property (you can query on this) for status setter
        :param new_status: <string> status to be set
        """
        if new_status == self.STATUS_INITIATED:
            self.initiated_at = datetime.utcnow()
        elif new_status == self.STATUS_RUNNING:
            self.started_at = datetime.utcnow()
        elif new_status == self.STATUS_SUCCESSFUL:
            self.completed_at = datetime.utcnow()
        elif new_status == WorkflowTask.STATUS_FAILED:
            self.completed_at = datetime.utcnow()

        self.__status = new_status

    @property
    def next_tasks(self):
        """
        Property to get next tasks associated with the current task
        :return:
        """
        return self._next_tasks

    @property
    def previous_tasks(self):
        """
        Property to get previous tasks associated with the current task
        :return:
        """
        return self._previous_tasks

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.STATUS_KEY: self.status,
            self.MESSAGE_KEY: self.message,
            self.RESOURCE_ID_KEY: self.resource_id,
            self.RESOURCE_TYPE_KEY: self.resource_type,
            self.TASK_TYPE_KEY: self.task_type,
            self.TASK_METADATA_KEY: self.task_metadata,
            self.PREVIOUS_TASK_IDS_KEY: [task.id for task in self.previous_tasks],
            self.NEXT_TASK_IDS_KEY: [task.id for task in self.next_tasks]
        }
