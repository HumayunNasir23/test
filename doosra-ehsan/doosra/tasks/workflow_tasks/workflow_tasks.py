"""
This file contains tasks for Workflows
"""
import logging

from doosra import db as doosradb
from doosra.models import WorkflowRoot, WorkflowTask
from doosra.tasks.celery_app import celery
from doosra.tasks.tasks_mapper import MAPPER
from doosra.tasks.workflow_tasks.workflow_tasks_base import WorkflowTasksBase

LOGGER = logging.getLogger(__name__)


@celery.task(name="workflow_manager", queue="workflow_queue")
def workflow_manager():
    """
    Manage workflows
    """
    workflow_roots = WorkflowRoot.query.filter(
        ~WorkflowRoot.executor_running,
        WorkflowRoot.status.in_(
            (
                WorkflowRoot.STATUS_PENDING,
                WorkflowRoot.STATUS_RUNNING,
                WorkflowRoot.STATUS_C_SUCCESSFULLY_WFC,
                WorkflowRoot.STATUS_C_W_FAILURE_WFC
            )
        )
    ).all()

    for workflow_root in workflow_roots:
        if workflow_root.status == WorkflowRoot.STATUS_PENDING:
            workflow_root.status = WorkflowRoot.STATUS_INITIATED
            doosradb.session.commit()

        workflow_executor.delay(workflow_root.id)


@celery.task(name="workflow_executor", base=WorkflowTasksBase, queue="workflow_initiator_queue")
def workflow_executor(workflow_root_id):
    """
    :param workflow_root_id:
    :return:
    """
    workflow_root = WorkflowRoot.query.filter_by(id=workflow_root_id).first()
    if not workflow_root:
        LOGGER.debug("Workflow Root ID: {} not found".format(workflow_root_id))
        return

    workflow_root.executor_running = True
    doosradb.session.commit()

    running_tasks_count = 0

    if workflow_root.status == WorkflowRoot.STATUS_INITIATED:
        workflow_root.status = WorkflowRoot.STATUS_RUNNING
        doosradb.session.commit()

        for task in workflow_root.next_tasks:
            task.status = WorkflowTask.STATUS_INITIATED
            task.in_focus = True
            doosradb.session.commit()

            try:
                run_func = MAPPER[task.resource_type][task.task_type]["RUN"]
            except KeyError as ex:
                task.status = WorkflowTask.STATUS_FAILED
                LOGGER.error("Task {task_type} for {resource_type} ill defined. Error: {error}".format(
                    task_type=task.task_type, resource_type=task.resource_type, error=str(ex)))
                task.message = "Internal Error: Task not defined properly"
                continue

            if not run_func:
                task.status = WorkflowTask.STATUS_FAILED
                LOGGER.error("Task {task_type} for {resource_type} does not have a 'RUN' function defined".format(
                    task_type=task.task_type, resource_type=task.resource_type))
                task.message = "Internal Error: Run function not defined"
                doosradb.session.commit()
                continue

            run_func.delay(task.id)
            running_tasks_count += 1
    elif workflow_root.status == WorkflowRoot.STATUS_RUNNING:
        iteration_tasks = workflow_root.in_focus_tasks
        for task in iteration_tasks:
            # This condition will only run for tasks which are appended to the task_ids from STATUS_C_SUCCESSFULLY case
            if task.status == WorkflowTask.STATUS_PENDING:
                if task.previous_tasks.filter_by(status=WorkflowTask.STATUS_SUCCESSFUL).count() \
                        != task.previous_tasks.count():
                    continue

                task.status = WorkflowTask.STATUS_INITIATED
                task.in_focus = True
                doosradb.session.commit()

                try:
                    run_func = MAPPER[task.resource_type][task.task_type]["RUN"]
                except KeyError as ex:
                    task.status = WorkflowTask.STATUS_FAILED
                    LOGGER.error("Task {task_type} for {resource_type} ill defined. Error: {error}".format(
                        task_type=task.task_type, resource_type=task.resource_type, error=str(ex)))
                    task.message = "Internal Error: Task not defined properly"
                    continue

                if not run_func:
                    task.status = WorkflowTask.STATUS_FAILED
                    LOGGER.error("Task {task_type} for {resource_type} does not have a 'RUN' function defined".format(
                        task_type=task.task_type, resource_type=task.resource_type))
                    task.message = "Internal Error: Run function not defined"
                    doosradb.session.commit()
                    continue

                run_func.delay(task.id)
                running_tasks_count += 1

            # If not yet picked by worker or If picked by worker and still in running state
            elif task.status in [
                WorkflowTask.STATUS_INITIATED, WorkflowTask.STATUS_RUNNING_WAIT_INITIATED,
                WorkflowTask.STATUS_RUNNING
            ]:
                running_tasks_count += 1

            # If picked by worker and completed running it but task needs to wait for poll (because it was long running)
            elif task.status == WorkflowTask.STATUS_RUNNING_WAIT:
                try:
                    wait_func = MAPPER[task.resource_type][task.task_type]["WAIT"]
                except KeyError as ex:
                    task.status = WorkflowTask.STATUS_FAILED
                    LOGGER.error("Task {task_type} for {resource_type} ill defined. Error: {error}".format(
                        task_type=task.task_type, resource_type=task.resource_type, error=str(ex)))
                    task.message = "Internal Error: Task not defined properly"
                    continue

                if not wait_func:
                    task.status = WorkflowTask.STATUS_FAILED
                    task.message = "Internal Error: Wait function not defined"
                    doosradb.session.commit()
                    continue

                task.status = WorkflowTask.STATUS_RUNNING_WAIT_INITIATED
                doosradb.session.commit()
                wait_func.delay(task.id)
                running_tasks_count += 1

            # If picked by worker, completed and was successful
            elif task.status == WorkflowTask.STATUS_SUCCESSFUL:
                task.in_focus = False
                doosradb.session.commit()

                iteration_task_ids = [iteration_task.id for iteration_task in iteration_tasks]
                for next_task in task.next_tasks.all():
                    if next_task.id not in iteration_task_ids:
                        iteration_tasks.append(next_task)

    if workflow_root.status == WorkflowRoot.STATUS_RUNNING and not running_tasks_count:
        if workflow_root.associated_tasks.filter(WorkflowTask.status == WorkflowTask.STATUS_FAILED).count():
            on_success_callbacks = workflow_root.callback_roots.filter_by(
                root_type=WorkflowRoot.ROOT_TYPE_ON_SUCCESS).all()
            for on_success_callback in on_success_callbacks:
                doosradb.session.delete(on_success_callback)

            workflow_root.status = WorkflowRoot.STATUS_C_W_FAILURE_WFC \
                if workflow_root.status_holding_callbacks_count else WorkflowRoot.STATUS_C_W_FAILURE
        else:
            on_failure_callbacks = workflow_root.callback_roots.filter_by(
                root_type=WorkflowRoot.ROOT_TYPE_ON_FAILURE).all()
            for on_failure_callback in on_failure_callbacks:
                doosradb.session.delete(on_failure_callback)

            workflow_root.status = WorkflowRoot.STATUS_C_SUCCESSFULLY_WFC \
                if workflow_root.status_holding_callbacks_count else WorkflowRoot.STATUS_C_SUCCESSFULLY

        doosradb.session.commit()
        on_hold_callback_roots = \
            workflow_root.callback_roots.filter(WorkflowRoot.status == WorkflowRoot.STATUS_ON_HOLD).all()
        for on_hold_callback_root in on_hold_callback_roots:
            on_hold_callback_root.status = WorkflowRoot.STATUS_PENDING

    elif workflow_root.status == WorkflowRoot.STATUS_C_SUCCESSFULLY_WFC and \
            not workflow_root.status_holding_callbacks_count:
        workflow_root.status = WorkflowRoot.STATUS_C_SUCCESSFULLY

    elif workflow_root.status == WorkflowRoot.STATUS_C_W_FAILURE_WFC and \
            not workflow_root.status_holding_callbacks_count:
        workflow_root.status = WorkflowRoot.STATUS_C_W_FAILURE

    workflow_root.executor_running = False
    doosradb.session.commit()
