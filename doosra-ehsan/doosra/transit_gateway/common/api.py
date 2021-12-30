import logging

from flask import Response, request, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import CREATED, SUCCESS
from doosra.models import IBMCloud, IBMTask
from doosra.transit_gateway.common import transit_common

LOGGER = logging.getLogger(__name__)


@transit_common.route('/ibm/transit_locations/<cloud_id>', methods=['POST'])
@authenticate
def sync_transit_locations(user_id, user, cloud_id):
    """
    Initiate sync Buckets for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.transit_gateway_tasks import task_list_transit_locations

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        LOGGER.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="TRANSIT-LOCATION").first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(task_list_transit_locations.delay(ibm_cloud.id).id, "TRANSIT-LOCATION", "SYNC", ibm_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    return Response(status=202)


@transit_common.route('/ibm/transit_locations/<cloud_id>', methods=['GET'])
@authenticate
def get_transit_locations(user_id, user, cloud_id):
    """
    Get available Buckets for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        LOGGER.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    task = ibm_cloud.ibm_tasks.filter_by(type="TRANSIT-LOCATION", action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({
        "locations": task.result['locations'],
        "task_id": task.id
    })
