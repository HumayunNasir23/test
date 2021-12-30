"""
APIs for Dedicated hosts
"""
import json
import logging

from flask import Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import CREATED, DEFAULT_LIMIT, MAX_PAGE_LIMIT
from doosra.ibm.dedicated_hosts import ibm_dedicated_hosts
from doosra.ibm.dedicated_hosts.consts import DEDICATED_HOST_CREATE, DEDICATED_HOST_DELETE, \
    DEDICATED_HOST_GROUP_CREATE, DEDICATED_HOST_GROUP_DELETE
from doosra.ibm.dedicated_hosts.schemas import ibm_create_dedicated_host_schema, \
    ibm_create_dedicated_host_group_schema, ibm_delete_dedicated_host_schema, ibm_delete_dedicated_host_group_schema, \
    ibm_sync_dh_profiles_schema
from doosra.models import IBMCloud, IBMTask, IBMDedicatedHost, IBMDedicatedHostGroup, IBMDedicatedHostProfile
from doosra.validate_json import validate_json

LOGGER = logging.getLogger(__name__)


@ibm_dedicated_hosts.route('/dedicated_hosts', methods=['POST'])
@authenticate
@validate_json(ibm_create_dedicated_host_schema)
def create_ibm_dedicated_host(user_id, user):
    """
    Add an IBM Dedicated Host
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.dedicated_host_tasks import task_create_dedicated_host

    data = request.get_json(force=True)
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not ibm_cloud:
        error_message = "No IBM cloud found with ID {id}".format(id=data['cloud_id'])
        LOGGER.info(error_message)
        return Response(error_message, status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        LOGGER.info(error_message)
        return Response(error_message, status=400)

    dedicated_host = \
        doosradb.session.query(IBMDedicatedHost).filter_by(
            name=data['name'], cloud_id=data['cloud_id'], region=data["region"]
        ).first()
    if dedicated_host:
        error_message = "ERROR_CONFLICTING_DEDICATED_HOST_NAME"
        LOGGER.info(error_message)
        return Response(error_message, status=409)

    if data.get("resource_group"):
        dh_resource_group = ibm_cloud.resource_groups.filter_by(name=data["resource_group"]).first()
        if not dh_resource_group:
            return Response(f"Resource Group {data['resource_group']} not found", 404)

    dh_profile = \
        ibm_cloud.dedicated_host_profiles.filter_by(
            id=data["dedicated_host_profile"]["id"], region=data["region"]
        ).first()
    if not dh_profile:
        return Response(f"Dedicated host profile with ID {data['dedicated_host_profile']['id']} not found", status=404)

    if data.get("dedicated_host_group_name"):
        dh_group = \
            ibm_cloud.dedicated_host_groups.filter_by(
                name=data["dedicated_host_group_name"], region=data["region"]
            ).first()
        if not dh_group:
            return Response(
                f"Dedicated host group '{data['dedicated_host_group_name']}' not found in region {data['region']}",
                status=404
            )
    elif data.get("dedicated_host_group") and "resource_group" in data["dedicated_host_group"]:
        dh_group_resource_group = \
            ibm_cloud.resource_groups.filter_by(name=data["dedicated_host_group"]["resource_group"]).first()
        if not dh_group_resource_group:
            return Response(f"Resource Group {data['dedicated_host_group']['resource_group']} not found", 404)

    ibm_task = IBMTask(None, "DEDICATED-HOST", "ADD", ibm_cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(ibm_task)
    doosradb.session.commit()

    task_create_dedicated_host.apply_async(kwargs={'ibm_task_id': ibm_task.id, 'data': data})

    LOGGER.info(DEDICATED_HOST_CREATE.format(email=user.email))
    return Response(json.dumps({"task_id": ibm_task.id}), status=202, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/<dedicated_host_id>', methods=['DELETE'])
@authenticate
@validate_json(ibm_delete_dedicated_host_schema)
def delete_ibm_dedicated_host(user_id, user, dedicated_host_id):
    """
    Delete an IBM Dedicated Host
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param dedicated_host_id: ID of the dedicated host
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.dedicated_host_tasks import task_delete_dedicated_host

    data = request.get_json(force=True)
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not ibm_cloud:
        error_message = "No IBM Cloud found with ID {id}".format(id=data['cloud_id'])
        LOGGER.info(error_message)
        return Response(error_message, status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        LOGGER.info(error_message)
        return Response(error_message, status=400)

    dedicated_host = ibm_cloud.dedicated_hosts.filter_by(id=dedicated_host_id).first()
    if not dedicated_host:
        return Response(status=404)

    if dedicated_host.instances.count():
        return Response("Please remove attached instances first", status=400)

    ibm_task = IBMTask(None, "DEDICATED-HOST", "DELETE", ibm_cloud.id)
    doosradb.session.add(ibm_task)
    doosradb.session.commit()

    task_delete_dedicated_host.apply_async(
        kwargs={'ibm_task_id': ibm_task.id, 'cloud_id': ibm_cloud.id, 'dedicated_host_id': dedicated_host_id}
    )

    LOGGER.info(DEDICATED_HOST_DELETE.format(dh_id=dedicated_host_id, email=user.email))
    return Response(json.dumps(ibm_task.to_json()), status=202, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts', methods=['GET'])
@authenticate
def list_ibm_dedicated_hosts(user_id, user):
    """
    Get IBM Dedicated Hosts
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud_query = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id)

    cloud_id = request.args.get("cloud_id")
    if cloud_id:
        ibm_cloud_query = ibm_cloud_query.filter_by(id=cloud_id)

    ibm_clouds = ibm_cloud_query.all()
    if cloud_id and not ibm_clouds:
        LOGGER.debug(f"IBM Cloud {cloud_id} not found for user {user_id}")
        return Response(status=404)
    elif not ibm_clouds:
        return Response(status=204)

    for ibm_cloud in ibm_clouds:
        if ibm_cloud.status != IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        return Response(error_message, status=400)

    start = request.args.get('start', 1, type=int)
    limit = request.args.get('limit', DEFAULT_LIMIT, type=int)

    if cloud_id:
        dedicated_hosts_query = doosradb.session.query(IBMDedicatedHost).filter_by(cloud_id=cloud_id)
    else:
        cloud_ids = set([ibm_cloud.id for ibm_cloud in ibm_clouds])
        dedicated_hosts_query = \
            doosradb.session.query(IBMDedicatedHost).filter(IBMDedicatedHost.cloud_id.in_(cloud_ids))

    region = request.args.get("region")
    if region:
        dedicated_hosts_query = dedicated_hosts_query.filter_by(region=region)

    dedicated_hosts_page = dedicated_hosts_query.paginate(start, limit, False, MAX_PAGE_LIMIT)

    if not dedicated_hosts_page.items:
        return Response(status=204)

    resp_json = {
        "items": [dedicated_host.to_json() for dedicated_host in dedicated_hosts_page.items],
        "previous": dedicated_hosts_page.prev_num if dedicated_hosts_page.has_prev else None,
        "next": dedicated_hosts_page.next_num if dedicated_hosts_page.has_next else None,
        "pages": dedicated_hosts_page.pages
    }
    return Response(json.dumps(resp_json), status=200, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/<dedicated_host_id>', methods=['GET'])
@authenticate
def get_ibm_dedicated_host(user_id, user, dedicated_host_id):
    """
    Get IBM Dedicated Hosts
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param dedicated_host_id: ID of the dedicated host
    """

    cloud_id = request.args.get("cloud_id")
    if not cloud_id:
        return Response("'cloud_id' is a required query parameter", status=400)

    region = request.args.get("region")
    if not region:
        return Response("'region' is a required query parameter", status=400)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        LOGGER.debug(f"IBM Cloud {cloud_id} not found for user {user_id}")
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        return Response(error_message, status=400)

    dedicated_host = ibm_cloud.dedicated_hosts.filter_by(id=dedicated_host_id, region=region).first()
    if not dedicated_host:
        LOGGER.debug(f"Dedicated host {dedicated_host_id} not found for user {user_id}")
        return Response(status=404)

    return Response(json.dumps(dedicated_host.to_json()), status=200, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/dedicated_host_groups', methods=['POST'])
@authenticate
@validate_json(ibm_create_dedicated_host_group_schema)
def create_ibm_dedicated_host_group(user_id, user):
    """
    Add an IBM Dedicated Host Group
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.dedicated_host_tasks import task_create_dedicated_host_group

    data = request.get_json(force=True)
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not ibm_cloud:
        error_message = "No IBM Cloud found with ID {id}".format(id=data['cloud_id'])
        LOGGER.info(error_message)
        return Response(error_message, status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        LOGGER.info(error_message)
        return Response(error_message, status=400)

    dedicated_host_group = \
        ibm_cloud.dedicated_host_groups.filter_by(
            name=data['name'], cloud_id=data['cloud_id'], region=data["region"]
        ).first()
    if dedicated_host_group:
        error_message = "ERROR_CONFLICTING_DEDICATED_HOST_GROUP_NAME"
        LOGGER.info(error_message)
        return Response(error_message, status=409)

    if data.get("resource_group"):
        dh_resource_group = ibm_cloud.resource_groups.filter_by(name=data["resource_group"]).first()
        if not dh_resource_group:
            return Response(f"Resource Group {data['resource_group']} not found", 404)

    ibm_task = IBMTask(None, "DEDICATED-HOST-GROUP", "ADD", ibm_cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(ibm_task)
    doosradb.session.commit()

    task_create_dedicated_host_group.apply_async(kwargs={'ibm_task_id': ibm_task.id, 'data': data})

    LOGGER.info(DEDICATED_HOST_GROUP_CREATE.format(email=user.email))
    return Response(json.dumps({"task_id": ibm_task.id}), status=202, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/dedicated_host_groups/<dedicated_host_group_id>', methods=['DELETE'])
@authenticate
@validate_json(ibm_delete_dedicated_host_group_schema)
def delete_ibm_dedicated_host_group(user_id, user, dedicated_host_group_id):
    """
    Delete an IBM Dedicated Host Group
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param dedicated_host_group_id: ID of the dedicated host group
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.dedicated_host_tasks import task_delete_dedicated_host_group

    data = request.get_json(force=True)
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not ibm_cloud:
        error_message = "No IBM Cloud found with ID {id}".format(id=data['cloud_id'])
        LOGGER.info(error_message)
        return Response(error_message, status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        LOGGER.info(error_message)
        return Response(error_message, status=400)

    dedicated_host_group = ibm_cloud.dedicated_host_groups.filter_by(id=dedicated_host_group_id).first()
    if not dedicated_host_group:
        return Response(status=404)

    if dedicated_host_group.dedicated_hosts.count():
        return Response("Please remove attached dedicated hosts first", status=400)

    ibm_task = IBMTask(None, "DEDICATED-HOST-GROUP", "DELETE", ibm_cloud.id)
    doosradb.session.add(ibm_task)
    doosradb.session.commit()

    task_delete_dedicated_host_group.apply_async(
        kwargs={
            'ibm_task_id': ibm_task.id, 'cloud_id': ibm_cloud.id, 'dedicated_host_group_id': dedicated_host_group_id
        }
    )

    LOGGER.info(DEDICATED_HOST_GROUP_DELETE.format(dh_group_id=dedicated_host_group_id, email=user.email))
    return Response(json.dumps(ibm_task.to_json()), status=202, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/dedicated_host_groups', methods=['GET'])
@authenticate
def list_ibm_dedicated_host_groups(user_id, user):
    """
    Get IBM Dedicated Host Group
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud_query = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id)

    cloud_id = request.args.get("cloud_id")
    if cloud_id:
        ibm_cloud_query = ibm_cloud_query.filter_by(id=cloud_id)

    ibm_clouds = ibm_cloud_query.all()
    if cloud_id and not ibm_clouds:
        LOGGER.debug(f"IBM Cloud {cloud_id} not found for user {user_id}")
        return Response(status=404)
    elif not ibm_clouds:
        return Response(status=204)

    for ibm_cloud in ibm_clouds:
        if ibm_cloud.status != IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        return Response(error_message, status=400)

    start = request.args.get('start', 1, type=int)
    limit = request.args.get('limit', DEFAULT_LIMIT, type=int)

    if cloud_id:
        dedicated_host_groups_query = doosradb.session.query(IBMDedicatedHostGroup).filter_by(cloud_id=cloud_id)
    else:
        cloud_ids = set([ibm_cloud.id for ibm_cloud in ibm_clouds])
        dedicated_host_groups_query = \
            doosradb.session.query(IBMDedicatedHostGroup).filter(IBMDedicatedHostGroup.cloud_id.in_(cloud_ids))

    region = request.args.get("region")
    if region:
        dedicated_host_groups_query = dedicated_host_groups_query.filter_by(region=region)

    dedicated_host_groups_page = dedicated_host_groups_query.paginate(start, limit, False, MAX_PAGE_LIMIT)

    if not dedicated_host_groups_page.items:
        return Response(status=204)

    resp_json = {
        "items": [dedicated_host_group.to_json() for dedicated_host_group in dedicated_host_groups_page.items],
        "previous": dedicated_host_groups_page.prev_num if dedicated_host_groups_page.has_prev else None,
        "next": dedicated_host_groups_page.next_num if dedicated_host_groups_page.has_next else None,
        "pages": dedicated_host_groups_page.pages
    }
    return Response(json.dumps(resp_json), status=200, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/dedicated_host_groups/<dedicated_host_group_id>', methods=['GET'])
@authenticate
def get_ibm_dedicated_host_group(user_id, user, dedicated_host_group_id):
    """
    Get IBM Dedicated Hosts
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param dedicated_host_group_id: ID of the dedicated host group
    """

    cloud_id = request.args.get("cloud_id")
    if not cloud_id:
        return Response("'cloud_id' is a required query parameter", status=400)

    region = request.args.get("region")
    if not region:
        return Response("'region' is a required query parameter", status=400)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        LOGGER.debug(f"IBM Cloud {cloud_id} not found for user {user_id}")
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        return Response(error_message, status=400)

    dedicated_host_group = ibm_cloud.dedicated_host_groups.filter_by(id=dedicated_host_group_id, region=region).first()
    if not dedicated_host_group:
        LOGGER.debug(f"Dedicated host group {dedicated_host_group_id} not found for user {user_id}")
        return Response(status=404)

    return Response(json.dumps(dedicated_host_group.to_json()), status=200, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/dedicated_host_profiles/sync', methods=['POST'])
@authenticate
@validate_json(ibm_sync_dh_profiles_schema)
def sync_dedicated_host_profiles(user_id, user):
    """
    Initiate sync Dedicated Host Profiles for IBM cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    # TODO: Limit the number of times this API can be called
    from doosra.tasks.ibm.dedicated_host_tasks import task_sync_dedicated_host_profiles

    data = request.get_json(force=True)
    cloud_id = data["cloud_id"]
    if not cloud_id:
        return Response("Query param 'cloud_id' is required", status=400)
    region = data["region"]
    if not region:
        return Response("Query param 'region' is required", status=400)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        LOGGER.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    ibm_task = ibm_cloud.ibm_tasks.filter_by(type="DEDICATED-HOST-PROFILE", region=region).first()
    if ibm_task and ibm_task.status == CREATED and not request.args.get('force'):
        return Response(json.dumps({"task_id": ibm_task.id}), status=202)
    elif ibm_task:
        doosradb.session.delete(ibm_task)

    ibm_task = IBMTask(None, "DEDICATED-HOST-PROFILE", "SYNC", ibm_cloud.id, region=region)
    doosradb.session.add(ibm_task)
    doosradb.session.commit()

    task_sync_dedicated_host_profiles.apply_async(
        kwargs={'ibm_task_id': ibm_task.id, 'cloud_id': ibm_cloud.id, 'region': region}, queue='sync_queue')
    return Response(json.dumps({"task_id": ibm_task.id}), status=202, mimetype="application/json")


@ibm_dedicated_hosts.route('/dedicated_hosts/dedicated_host_profiles', methods=['GET'])
@authenticate
def list_ibm_dedicated_host_profiles(user_id, user):
    """
    List all IBM Dedicated Host Profiles
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud_query = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id)

    cloud_id = request.args.get("cloud_id")
    if cloud_id:
        ibm_cloud_query = ibm_cloud_query.filter_by(id=cloud_id)

    ibm_clouds = ibm_cloud_query.all()
    if cloud_id and not ibm_clouds:
        LOGGER.debug(f"IBM Cloud {cloud_id} not found for user {user_id}")
        return Response(status=404)
    elif not ibm_clouds:
        return Response(status=204)

    for ibm_cloud in ibm_clouds:
        if ibm_cloud.status != IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        return Response(error_message, status=400)

    start = request.args.get('start', 1, type=int)
    limit = request.args.get('limit', DEFAULT_LIMIT, type=int)

    if cloud_id:
        dedicated_host_profiles_query = doosradb.session.query(IBMDedicatedHostProfile).filter_by(cloud_id=cloud_id)
    else:
        cloud_ids = set([ibm_cloud.id for ibm_cloud in ibm_clouds])
        dedicated_host_profiles_query = \
            doosradb.session.query(IBMDedicatedHostProfile).filter(IBMDedicatedHostProfile.cloud_id.in_(cloud_ids))

    region = request.args.get("region")
    if region:
        dedicated_host_profiles_query = dedicated_host_profiles_query.filter_by(region=region)

    dedicated_host_profiles_page = dedicated_host_profiles_query.paginate(start, limit, False, MAX_PAGE_LIMIT)

    if not dedicated_host_profiles_page.items:
        return Response(status=204)

    resp_json = {
        "items": [dedicated_host_profile.to_json() for dedicated_host_profile in dedicated_host_profiles_page.items],
        "previous": dedicated_host_profiles_page.prev_num if dedicated_host_profiles_page.has_prev else None,
        "next": dedicated_host_profiles_page.next_num if dedicated_host_profiles_page.has_next else None,
        "pages": dedicated_host_profiles_page.pages
    }
    return Response(
        json.dumps(resp_json), status=200,
        mimetype="application/json"
    )


@ibm_dedicated_hosts.route('/dedicated_hosts/dedicated_host_profiles/<dedicated_host_profile_id>', methods=['GET'])
@authenticate
def get_ibm_dedicated_host_profile(user_id, user, dedicated_host_profile_id):
    """
    Get IBM Dedicated Hosts
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param dedicated_host_profile_id: ID of the dedicated host profile
    """

    cloud_id = request.args.get("cloud_id")
    if not cloud_id:
        return Response("'cloud_id' is a required query parameter", status=400)

    region = request.args.get("region")
    if not region:
        return Response("'region' is a required query parameter", status=400)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        LOGGER.debug(f"IBM Cloud {cloud_id} not found for user {user_id}")
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        error_message = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        return Response(error_message, status=400)

    dedicated_host_profile = \
        ibm_cloud.dedicated_host_profiles.filter_by(id=dedicated_host_profile_id, region=region).first()
    if not dedicated_host_profile:
        LOGGER.debug(f"Dedicated host profile {dedicated_host_profile_id} not found for user {user_id}")
        return Response(status=404)

    return Response(json.dumps(dedicated_host_profile.to_json()), status=200, mimetype="application/json")
