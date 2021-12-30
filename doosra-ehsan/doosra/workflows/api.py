import json
import logging
from datetime import datetime

from flask import request, Response

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import DEFAULT_LIMIT, MAX_PAGE_LIMIT
from doosra.models import WorkflowRoot, WorkflowTask
from doosra.workflows import ibm_workflows
from doosra.workflows.consts import DATE_TIME_FORMAT
from doosra.workflows.utils import get_resource_json

LOGGER = logging.getLogger(__name__)


@ibm_workflows.route('/workflows', methods=['GET'])
@authenticate
def list_workflows(user_id, user):
    """
    List all workflows (or based on filters)
    """
    start = request.args.get('start', 1, type=int)
    limit = request.args.get('limit', DEFAULT_LIMIT, type=int)

    filter_q = request.args.get("filter")
    if filter_q:
        if filter_q.lower() not in ["true", "false"]:
            return Response("Request param 'filter' should be 'true' or 'false'", status=400)

        filter_q = filter_q.lower() == "true"

    workflow_roots_query = doosradb.session.query(WorkflowRoot).filter_by(
        project_id=user.project.id, root_type=WorkflowRoot.ROOT_TYPE_NORMAL
    )

    if filter_q:
        statuses = request.args.get("statuses")
        statuses = statuses.split(",") if statuses else list()

        status_list = list()
        for status in statuses:
            if "'" in status or '"' in status:
                return Response("Query param 'statuses' should not include quotes", status=400)

            if status == "PENDING":
                status_list.extend(
                    [WorkflowRoot.STATUS_INITIATED, WorkflowRoot.STATUS_PENDING, WorkflowRoot.STATUS_RUNNING]
                )
            elif status == "COMPLETED_SUCCESSFULLY":
                status_list.append(WorkflowRoot.STATUS_C_SUCCESSFULLY)
            elif status == "COMPLETED_WITH_FAILURE":
                status_list.append(WorkflowRoot.STATUS_C_W_FAILURE)
            else:
                return Response(
                    "Elements of query param 'statuses' should be one of 'PENDING', 'COMPLETED_SUCCESSFULLY', "
                    "'COMPLETED_WITH_FAILURE'",
                    status=400
                )

        natures = request.args.get("natures")
        natures = natures.split(",") if natures else list()

        for nature in natures:
            if "'" in nature or '"' in nature:
                return Response("Query param 'natures' should not include quotes", status=400)
            if len(nature) > 128:
                return Response("Length of query param 'natures' should be less than 128", status=400)

        name_like = request.args.get("name_like")
        if name_like and len(name_like) > 128:
            return Response("Length of query param 'name' should be less than 128", status=400)

        created_after = request.args.get("created_after")
        if created_after:
            try:
                created_after = datetime.strptime(created_after, DATE_TIME_FORMAT)
            except ValueError as ex:
                return Response(str(ex), status=400)

        created_before = request.args.get("created_before")
        if created_before:
            try:
                created_before = datetime.strptime(created_before, DATE_TIME_FORMAT)
            except ValueError as ex:
                return Response(str(ex), status=400)

        if created_after and created_before and created_after > created_before:
            return Response(
                "Query param 'created_after' should be less than 'created_before' if both are provided", status=400
            )

        if status_list:
            workflow_roots_query = workflow_roots_query.filter(WorkflowRoot.status.in_(status_list))

        if natures:
            workflow_roots_query = workflow_roots_query.filter(WorkflowRoot.workflow_nature.in_(natures))

        if name_like:
            workflow_roots_query = \
                workflow_roots_query.filter(WorkflowRoot.workflow_name.like(f"%{name_like}%"))

        if created_after:
            workflow_roots_query = workflow_roots_query.filter(WorkflowRoot.created_at > created_after)

        if created_before:
            workflow_roots_query = workflow_roots_query.filter(WorkflowRoot.created_at < created_before)

    workflow_roots_query = workflow_roots_query.order_by(WorkflowRoot.created_at.desc())
    workflow_roots = workflow_roots_query.paginate(start, limit, False, MAX_PAGE_LIMIT)

    if not workflow_roots.items:
        return Response(status=204)

    resp_json = {
        "items": [workflow_root.to_json(metadata=True) for workflow_root in workflow_roots.items],
        "previous": workflow_roots.prev_num if workflow_roots.has_prev else None,
        "next": workflow_roots.next_num if workflow_roots.has_next else None,
        "pages": workflow_roots.pages
    }
    return Response(
        json.dumps(resp_json), status=200,
        mimetype="application/json"
    )


@ibm_workflows.route('/workflows/<root_id>', methods=['GET'])
@authenticate
def get_workflow(user_id, user, root_id):
    """
    Get a workflow by ID
    """
    workflow_root = doosradb.session.query(WorkflowRoot).filter_by(
        id=root_id, project_id=user.project.id, root_type=WorkflowRoot.ROOT_TYPE_NORMAL
    ).first()
    if not workflow_root:
        LOGGER.info(f"No WorkflowRoot task exists with this ID {root_id}")
        return Response(status=404)

    resp = workflow_root.to_json()
    resp["resource_json"] = get_resource_json(workflow_root=workflow_root)

    return Response(json.dumps(resp), status=200, mimetype="application/json")


@ibm_workflows.route('/workflows/<root_id>/in-focus', methods=['GET'])
@authenticate
def list_in_focus_tasks(user_id, user, root_id):
    """
    List all in_focus task for a WorkflowRoot
    """
    workflow_root = doosradb.session.query(WorkflowRoot).filter_by(
        id=root_id, project_id=user.project.id, root_type=WorkflowRoot.ROOT_TYPE_NORMAL
    ).first()
    if not workflow_root:
        LOGGER.info(f"No WorkflowRoot task exists with this ID {root_id}")
        return Response(status=404)

    response = {
        "task_id": workflow_root.id,
        "in_focus_tasks": [task.to_json() for task in workflow_root.in_focus_tasks],
        "status": workflow_root.status
    }
    return Response(json.dumps(response), status=200, mimetype="application/json")


@ibm_workflows.route('/workflows/<root_id>/tasks/<task_id>', methods=['GET'])
@authenticate
def get_workflow_task(user_id, user, root_id, task_id):
    """
    Get WorkflowTask provided root_id and task_id
    """
    workflow_task = doosradb.session.query(WorkflowTask).filter_by(id=task_id, root_id=root_id).first()
    if not workflow_task or (workflow_task.root.project_id != user.project.id) or \
            workflow_task.root.root_type != WorkflowRoot.ROOT_TYPE_NORMAL:
        LOGGER.info(f"No WorkflowTask task exists with this ID {task_id}")
        return Response(status=404)

    return Response(json.dumps(workflow_task.to_json()), status=200, mimetype="application/json")
