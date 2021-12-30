from flask import current_app, request, Response, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import CREATED, SUCCESS
from doosra.ibm.common import ibm_common
from doosra.models import IBMCloud, IBMTask, IBMVpcNetwork, SecondaryVolumeMigrationTask


@ibm_common.route('/tasks/<task_id>', methods=['GET'])
@authenticate
def get_task_details(user_id, user, task_id):
    """
    Get task details for a task, provided its task_id
    """
    task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not task:
        current_app.logger.info("No IBM task exists with this id {}".format(task_id))
        return Response(status=404)

    return jsonify(task.to_json())


@ibm_common.route('/secondary-volume-migration-tasks/<task_id>', methods=['GET'])
@authenticate
def get_secondary_volume_migration_task_details(user_id, user, task_id):
    """
    Get task details for a secondary volume migration task, provided its task_id
    """
    task = doosradb.session.query(SecondaryVolumeMigrationTask).filter_by(id=task_id).first()
    if not task:
        current_app.logger.info("No IBM task exists with this id {}".format(task_id))
        return Response(status=404)

    return jsonify(task.to_json())


@ibm_common.route('/sync-regions/<cloud_id>', methods=['POST'])
@authenticate
def sync_regions(user_id, user, cloud_id):
    """
    Initiate sync regions for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_regions

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="REGION").first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "REGION", "SYNC", ibm_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_regions.apply_async(kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/regions/<cloud_id>', methods=['GET'])
@authenticate
def get_regions(user_id, user, cloud_id):
    """
    Get available regions for a IBM cloud account
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="REGION", action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"regions": task.result['regions'], "task_id": task.id})


@ibm_common.route('/sync-zones/<cloud_id>/region/<region>', methods=['POST'])
@authenticate
def sync_zones(user_id, user, cloud_id, region):
    """
    Initiate sync zone for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_zones

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="ZONE", region=region).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "ZONE", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_zones.apply_async(
        kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id, 'region': region}, queue='sync_queue')

    return Response(status=202)


@ibm_common.route('/zones/<cloud_id>/region/<region>', methods=['GET'])
@authenticate
def get_zones(user_id, user, cloud_id, region):
    """
    Get available zones for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="ZONE", region=region, action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"zones": task.result['zones'], "task_id": task.id})


@ibm_common.route('/sync-resource-groups/<cloud_id>', methods=['POST'])
@authenticate
def sync_resource_groups(user_id, user, cloud_id):
    """
    Initiate sync zone for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_resource_groups

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="RESOURCE-GROUP").first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "RESOURCE-GROUP", "SYNC", ibm_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_resource_groups.apply_async(kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/resource-groups/<cloud_id>', methods=['GET'])
@authenticate
def get_resource_groups(user_id, user, cloud_id):
    """
    Get available resource groups for an IBM cloud account
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="RESOURCE-GROUP", action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"resource_groups": task.result['resource_groups'], "task_id": task.id})


@ibm_common.route('/sync-address-prefixes/<vpc_id>', methods=['POST'])
@authenticate
def sync_address_prefixes(user_id, user, vpc_id):
    """
    Initiate sync address prefixes for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_ibm_address_prefixes

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No VPC found with ID {vpc_id}".format(vpc_id=vpc_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=vpc.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=vpc.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="ADDRESS-PREFIX").first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "ADDRESS-PREFIX", "SYNC", ibm_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_ibm_address_prefixes.apply_async(kwargs={'vpc_id': vpc.id, 'task_id': task.id}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/address-prefixes/<vpc_id>', methods=['GET'])
@authenticate
def get_address_prefixes(user_id, user, vpc_id):
    """
    Get available address prefixes for an IBM VPC network
    """
    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No VPC found with ID {vpc_id}".format(vpc_id=vpc_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=vpc.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=vpc.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="ADDRESS-PREFIX", action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"address_prefixes": task.result, "task_id": task.id})


@ibm_common.route('/sync_images/<cloud_id>/region/<region>', methods=['POST'])
@authenticate
def sync_images(user_id, user, cloud_id, region):
    """
    Initiate sync images for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_images

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="IMAGE", region=region).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "IMAGE", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_images.apply_async(
        kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id, 'region': region}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/images/<cloud_id>/region/<region>', methods=['GET'])
@authenticate
def get_images(user_id, user, cloud_id, region):
    """
    Get available images for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="IMAGE", region=region, action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"images": task.result['images'], "task_id": task.id})


@ibm_common.route('/sync_operating_systems/<cloud_id>/region/<region>', methods=['POST'])
@authenticate
def sync_operating_systems(user_id, user, cloud_id, region):
    """
    Initiate sync operating systems for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_operating_systems

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="OPERATING-SYSTEM", region=region).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "OPERATING-SYSTEM", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_operating_systems.apply_async(
        kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id, 'region': region}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/operating_systems/<cloud_id>/region/<region>', methods=['GET'])
@authenticate
def get_operating_systems(user_id, user, cloud_id, region):
    """
    Get available operating systems for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="OPERATING-SYSTEM", region=region, action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"operating_systems": task.result['operating_systems'], "task_id": task.id})


@ibm_common.route('/sync_instance_profiles/<cloud_id>/region/<region>', methods=['POST'])
@authenticate
def sync_instance_profiles(user_id, user, cloud_id, region):
    """
    Initiate sync instance profiles for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_instance_profiles

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="INSTANCE-PROFILE", region=region).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "INSTANCE-PROFILE", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_instance_profiles.apply_async(
        kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id, 'region': region}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/instance_profiles/<cloud_id>/region/<region>', methods=['GET'])
@authenticate
def get_instance_profiles(user_id, user, cloud_id, region):
    """
    Get available instance profiles for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="INSTANCE-PROFILE", region=region, action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"instance_profiles": task.result['instance_profiles'], "task_id": task.id})


@ibm_common.route('/sync_volume_profiles/<cloud_id>/region/<region>', methods=['POST'])
@authenticate
def sync_volume_profiles(user_id, user, cloud_id, region):
    """
    Initiate sync volume profiles for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.ibm_tasks import task_get_volume_profiles

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="VOLUME-PROFILE", region=region).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "VOLUME-PROFILE", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_volume_profiles.apply_async(
        kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id, 'region': region}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/volume_profiles/<cloud_id>/region/<region>', methods=['GET'])
@authenticate
def get_volume_profiles(user_id, user, cloud_id, region):
    """
    Get available volume profiles for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="VOLUME-PROFILE", region=region, action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"volume_profiles": task.result['volume_profiles'], "task_id": task.id})


@ibm_common.route('/buckets/<cloud_id>/region/<region>', methods=['POST'])
@authenticate
def sync_cos_buckets(user_id, user, cloud_id, region):
    """
    Initiate sync Buckets for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    # TODO all parameter is needed all or qcow2
    from doosra.tasks.other.ibm_tasks import task_get_cos_buckets

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="BUCKET", region=region).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = IBMTask(None, "BUCKET", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_cos_buckets.apply_async(
        kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id, 'region': region}, queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/buckets/<cloud_id>/region/<region>', methods=['GET'])
@authenticate
def get_cos_buckets(user_id, user, cloud_id, region):
    """
    Get available Buckets for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="BUCKET", region=region, action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"buckets": task.result['buckets'], "task_id": task.id})


@ibm_common.route('/buckets-objects/<cloud_id>/region/<region>', methods=['POST'])
@authenticate
def sync_cos_buckets_objects(user_id, user, cloud_id, region):
    """
    Initiate sync Buckets and its Objects for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    # TODO all parameter is needed all or qcow2
    from doosra.tasks.other.ibm_tasks import task_get_cos_buckets

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    sync_task = ibm_cloud.ibm_tasks.filter_by(type="BUCKET-OBJECT", region=region).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)
    primary_objects = request.args.get('primary_objects', True)
    task = IBMTask(None, "BUCKET-OBJECT", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_cos_buckets.apply_async(
        kwargs={'cloud_id': ibm_cloud.id, 'task_id': task.id, 'region': region, 'get_objects': True,
                'primary_objects': primary_objects},
        queue='sync_queue')
    return Response(status=202)


@ibm_common.route('/buckets-objects/<cloud_id>/region/<region>', methods=['GET'])
@authenticate
def get_cos_buckets_objects(user_id, user, cloud_id, region):
    """
    Get available Buckets and its Objects for a IBM cloud account within an IBM region
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = ibm_cloud.ibm_tasks.filter_by(type="BUCKET-OBJECT", region=region, action="SYNC").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify({"buckets": task.result['buckets'], "task_id": task.id})
