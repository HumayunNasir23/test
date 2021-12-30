from flask import current_app, jsonify, request, Response

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import CREATED, SUCCESS
from doosra.gcp.common import gcp
from doosra.models import GcpCloudProject, GcpTask


@gcp.route('/tasks/<task_id>', methods=['GET'])
@authenticate
def get_task_details(user_id, user, task_id):
    """
    Get task details for a task, provided its task_id
    """
    task = doosradb.session.query(GcpTask).filter_by(id=task_id).first()
    if not task:
        current_app.logger.info("No GCP task exists with this id {}".format(task_id))
        return Response(status=404)

    return jsonify(task.to_json())


@gcp.route('/sync-regions/<cloud_project_id>', methods=['POST'])
@authenticate
def sync_regions(user_id, user, cloud_project_id):
    """
    Initiate sync for cloud project.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.gcp_tasks import task_get_regions

    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=cloud_project_id, user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    sync_task = project.gcp_cloud.gcp_tasks.filter_by(type="REGION", resource_id=project.id).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = GcpTask(task_get_regions.delay(cloud_project_id).id, "REGION", "SYNC", project.gcp_cloud.id, project.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    return Response(status=202)


@gcp.route('/regions/<cloud_project_id>', methods=['GET'])
@authenticate
def get_regions(user_id, user, cloud_project_id):
    """
    Get region across a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=cloud_project_id, user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    task = project.gcp_cloud.gcp_tasks.filter_by(type="REGION", resource_id=project.id).first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"regions": task.result['regions'], "task_id": task.id})


@gcp.route('/sync-zones/<cloud_project_id>', methods=['POST'])
@authenticate
def sync_zones(user_id, user, cloud_project_id):
    """
    Initiate sync for cloud project.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.gcp_tasks import task_get_zones

    project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    sync_task = project.gcp_cloud.gcp_tasks.filter_by(type="ZONE", resource_id=project.id).first()
    if sync_task and sync_task.status == 'SYNCING' and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = GcpTask(task_get_zones.delay(cloud_project_id).id, "ZONE", "SYNC", project.gcp_cloud.id, project.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    return Response(status=202)


@gcp.route('/zones/<cloud_project_id>', methods=['GET'])
@authenticate
def get_vpc_zones(user_id, user, cloud_project_id):
    """
    Get zones across a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    task = project.gcp_cloud.gcp_tasks.filter_by(type="ZONE", resource_id=project.id).first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != "SUCCESS":
        return jsonify({"status": task.status})

    return jsonify({"zones": task.result['zones'], "task_id": task.id})


@gcp.route('/sync-images/<cloud_project_id>', methods=['POST'])
@authenticate
def sync_images(user_id, user, cloud_project_id):
    """
    Initiate sync for cloud project.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.gcp_tasks import task_get_images

    project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    sync_task = project.gcp_cloud.gcp_tasks.filter_by(type="IMAGE", resource_id=project.id).first()
    if sync_task and sync_task.status == 'SYNCING' and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = GcpTask(task_get_images.delay(cloud_project_id).id, "IMAGE", "SYNC", project.gcp_cloud.id, project.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    return Response(status=202)


@gcp.route('/images/<cloud_project_id>', methods=['GET'])
@authenticate
def get_images(user_id, user, cloud_project_id):
    """
    Get images across a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    task = project.gcp_cloud.gcp_tasks.filter_by(type="IMAGE", resource_id=project.id).first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != "SUCCESS":
        return jsonify({"status": task.status})

    return jsonify({"images": task.result['images'], "task_id": task.id})


@gcp.route('/sync-machine-types/<cloud_project_id>', methods=['POST'])
@authenticate
def sync_machine_types(user_id, user, cloud_project_id):
    """
    Initiate sync for cloud project.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.gcp_tasks import task_get_machine_type

    project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    sync_task = project.gcp_cloud.gcp_tasks.filter_by(type="MTYPE", resource_id=project.id).first()
    if sync_task and sync_task.status == 'SYNCING' and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = GcpTask(task_get_machine_type.delay(cloud_project_id).id, "MTYPE", "SYNC", project.gcp_cloud.id, project.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    return Response(status=202)


@gcp.route('/machine-types/<cloud_project_id>', methods=['GET'])
@authenticate
def get_machine_types(user_id, user, cloud_project_id):
    """
    Get machine types in a zone across a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    task = project.gcp_cloud.gcp_tasks.filter_by(type="MTYPE", resource_id=project.id).first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != "SUCCESS":
        return jsonify({"status": task.status})

    return jsonify({"machine_types": task.result['machine_types'], "task_id": task.id})
