import json

from flask import current_app, request, Response, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.utils import decrypt_api_key
from doosra.common.utils import encrypt_api_key
from doosra.ibm.clouds import ibm_clouds
from doosra.ibm.clouds.consts import AUTHENTICATING
from doosra.ibm.clouds.schemas import discovery_schema, ibm_cloud_account_schema, ibm_cloud_update_schema, \
    ibm_update_dashboard_setting_schema
from doosra.models import IBMCloud, IBMServiceCredentials, IBMTask, IBMDashboardSetting
from doosra.validate_json import validate_json
from .mappers import IBM_DASHBOARD_RESOURCE_TYPE_MAPPER
from doosra.common.consts import VALID, DELETING


@ibm_clouds.route('/clouds', methods=['POST'])
@validate_json(ibm_cloud_account_schema)
@authenticate
def add_ibm_cloud_account(user_id, user):
    """
    Add an IBM Cloud Account
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks import task_process_new_ibm_cloud_account

    data = request.get_json(force=True)
    existing_cloud = doosradb.session.query(IBMCloud).filter(IBMCloud.name == data["name"],
                                                             IBMCloud.project_id == user.project.id,
                                                             IBMCloud.status != DELETING).first()
    if existing_cloud:
        return Response("ERROR_SAME_NAME", status=409)

    existing_clouds = doosradb.session.query(IBMCloud).filter(IBMCloud.project_id == user.project.id,
                                                              IBMCloud.status != DELETING).all()
    for cloud in existing_clouds:
        if cloud.verify_api_key(data['api_key']):
            return Response("ERROR_SAME_API_KEY, cloud_id={}".format(cloud.id), status=409)

    cloud = IBMCloud(data["name"], data["api_key"], user.project.id)
    if data.get("resource_instance_id"):
        cloud.service_credentials = IBMServiceCredentials(data["resource_instance_id"])

    if data.get("access_key_id") and data.get("secret_access_key"):
        cloud.service_credentials.access_key_id = encrypt_api_key(data["access_key_id"])
        cloud.service_credentials.secret_access_key = encrypt_api_key(data["secret_access_key"])

    doosradb.session.add(cloud)
    doosradb.session.commit()
    task_process_new_ibm_cloud_account.apply_async(queue='sync_queue', args=[cloud.id])
    return Response(json.dumps(cloud.to_json()), status=201, mimetype="application/json")


@ibm_clouds.route('/clouds/<cloud_id>', methods=['GET'])
@authenticate
def get_ibm_cloud_account(user_id, user, cloud_id):
    """
    Get an IBM Cloud Account
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param cloud_id: cloud_id for Cloud object
    :return: Response object from flask package
    """
    ibm_cloud_account = doosradb.session.query(IBMCloud).filter(IBMCloud.id == cloud_id,
                                                                IBMCloud.project_id == user.project.id,
                                                                IBMCloud.status != DELETING).first()
    if not ibm_cloud_account:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=204)

    cloud_account_json = ibm_cloud_account.to_json()
    return jsonify(cloud_account_json)


@ibm_clouds.route('/clouds', methods=['GET'])
@authenticate
def list_ibm_cloud_account(user_id, user):
    """
    List all IBM Cloud Accounts
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter(IBMCloud.project_id == user.project.id,
                                                                 IBMCloud.status != DELETING).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    cloud_accounts_json = list()
    for ibm_cloud_account in ibm_cloud_accounts:
        cloud_accounts_json.append(ibm_cloud_account.to_json())

    return jsonify(cloud_accounts_json)


@ibm_clouds.route('/clouds/<cloud_id>', methods=['PATCH'])
@authenticate
@validate_json(ibm_cloud_update_schema)
def update_ibm_cloud_account(user_id, user, cloud_id):
    """
    Update an IBM Cloud Account
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param cloud_id: cloud_id for Cloud object
    :return: Response object from flask package
    """
    from doosra.tasks import task_process_new_ibm_cloud_account

    data = request.get_json(force=True)
    force = request.args.get("force")

    cloud_account = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not cloud_account:
        current_app.logger.info("No IBM cloud account found with ID {}".format(cloud_id))
        return Response(status=404)

    if force:
        cloud_account.status = AUTHENTICATING
        doosradb.session.commit()

    if not cloud_account.service_credentials:
        if data.get("resource_instance_id"):
            cloud_account.service_credentials = IBMServiceCredentials(data["resource_instance_id"])
            doosradb.session.commit()

        if data.get("access_key_id") and data.get("secret_access_key"):
            cloud_account.service_credentials.access_key_id = encrypt_api_key(data["access_key_id"])
            cloud_account.service_credentials.secret_access_key = encrypt_api_key(data["secret_access_key"])
            doosradb.session.commit()

    if not cloud_account.service_credentials.access_key_id and not cloud_account.service_credentials.secret_access_key:
        if data.get("access_key_id") and data.get("secret_access_key"):
            cloud_account.service_credentials.access_key_id = encrypt_api_key(data["access_key_id"])
            cloud_account.service_credentials.secret_access_key = encrypt_api_key(data["secret_access_key"])
            doosradb.session.commit()

    elif data.get("resource_instance_id") and data["resource_instance_id"] != \
            cloud_account.service_credentials.resource_instance_id:
        cloud_account.service_credentials.resource_instance_id = data["resource_instance_id"]
        doosradb.session.commit()

    elif data.get("access_key_id") and data["access_key_id"] != \
            decrypt_api_key(cloud_account.service_credentials.access_key_id) and \
            data.get("secret_access_key") and data["secret_access_key"] != \
            decrypt_api_key(cloud_account.service_credentials.secret_access_key):

        cloud_account.service_credentials.access_key_id = encrypt_api_key(data.get("access_key_id"))
        cloud_account.service_credentials.secret_access_key = encrypt_api_key(data.get("secret_access_key"))
        cloud_account.status = AUTHENTICATING

    if data.get("name") and data["name"] != cloud_account.name:
        existing_cloud = doosradb.session.query(IBMCloud).filter_by(name=data["name"],
                                                                    project_id=user.project.id).first()
        if existing_cloud:
            return Response("ERROR_SAME_NAME", status=409)

        cloud_account.name = data["name"]
        doosradb.session.commit()

    if data.get("api_key") and data["api_key"] != decrypt_api_key(cloud_account.api_key):
        existing_clouds = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
        for cloud in existing_clouds:
            if cloud.verify_api_key(data['api_key']):
                return Response("ERROR_SAME_API_KEY, cloud_id={}".format(cloud.id), status=409)

        cloud_account.api_key = encrypt_api_key(data["api_key"])
        cloud_account.status = AUTHENTICATING

    if data.get('resource_instance_id'):
        cloud_account.status = AUTHENTICATING
        cloud_account.service_credential = data['resource_instance_id']

    if data.get("access_key_id") and data.get("secret_access_key"):
        cloud_account.status = AUTHENTICATING
        cloud_account.service_credential = encrypt_api_key(data["access_key_id"]), \
                                           encrypt_api_key(data["secret_access_key"])

    doosradb.session.commit()
    if cloud_account.status == AUTHENTICATING:
        task_process_new_ibm_cloud_account.apply_async(queue='sync_queue', args=[cloud_account.id])

    return jsonify(cloud_account.to_json())


@ibm_clouds.route('/clouds/<cloud_id>', methods=['DELETE'])
@authenticate
def delete_ibm_cloud_account(user_id, user, cloud_id):
    """
    Delete an IBM Cloud Account
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param cloud_id: cloud_id for Cloud object
    :return: Response object from flask package
    """
    ibm_cloud_account = doosradb.session.query(IBMCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not ibm_cloud_account:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    ibm_cloud_account.status = DELETING
    doosradb.session.commit()
    return Response(status=204)


@ibm_clouds.route('/clouds/sync', methods=['POST'])
@authenticate
@validate_json(discovery_schema)
def run_discovery(user_id, user):
    from doosra.tasks.other.ibm_tasks import task_fire_discovery

    data = request.get_json(force=True)

    cloud = doosradb.session.query(IBMCloud).filter_by(id=data['cloud_id'], project_id=user.project.id, status=VALID).first()
    if not cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=data['cloud_id']))
        return Response(status=400)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(task_fire_discovery.delay(cloud.id).id, "CLOUD", "SYNC", cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_clouds.route('/clouds/dashboard-settings', methods=['GET'])
@authenticate
def list_ibm_cloud_dashboard_settings(user_id, user):
    """
    List all IBM Cloud Accounts dashboard settings with their counts
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    dashboard_settings = doosradb.session.query(IBMDashboardSetting).filter_by(user_id=user_id).all()
    if not dashboard_settings:
        for resource in IBM_DASHBOARD_RESOURCE_TYPE_MAPPER.keys():
            dashboard_setting = IBMDashboardSetting(
                resource, user_id, IBM_DASHBOARD_RESOURCE_TYPE_MAPPER[resource]["pin_status"])
            doosradb.session.add(dashboard_setting)
            doosradb.session.commit()
            dashboard_settings.append(dashboard_setting)

    dashboard_settings_resp = list()
    cloud_id = request.args.get('cloud_id')
    if not cloud_id:
        clouds = doosradb.session.query(IBMCloud.id).filter_by(project_id=user.project.id).all()
    else:
        clouds = doosradb.session.query(IBMCloud.id).filter_by(id=cloud_id).all()

    for setting in dashboard_settings:
        resource_count = 0
        for cloud in clouds:
            if setting.name == "Kubernetes Clusters":
                resource_count += doosradb.session.query(
                    IBM_DASHBOARD_RESOURCE_TYPE_MAPPER[setting.name]['resource_type']).filter_by(
                    cloud_id=cloud.id, cluster_type="kubernetes").count()
            else:
                resource_count += doosradb.session.query(
                    IBM_DASHBOARD_RESOURCE_TYPE_MAPPER[setting.name]['resource_type']).filter_by(
                    cloud_id=cloud.id).count()

        settings_json = setting.to_json()
        settings_json["count"] = resource_count

        dashboard_settings_resp.append(settings_json)

    return Response(json.dumps(dashboard_settings_resp), status=200, mimetype="application/json")


@ibm_clouds.route('/clouds/dashboard-settings', methods=['PATCH'])
@authenticate
@validate_json(ibm_update_dashboard_setting_schema)
def update_ibm_cloud_dashboard_setting(user_id, user):
    """
    Update an IBM Cloud Account Dashboard Setting
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param cloud_id: cloud_id for Cloud object
    :return: Response object from flask package
    """
    data = request.get_json(force=True)

    dashboard_settings_list = list()
    for setting in data:
        dashboard_setting = doosradb.session.query(IBMDashboardSetting).filter(
            IBMDashboardSetting.id == setting['id'], IBMDashboardSetting.user_id == user_id).first()
        if not dashboard_setting:
            current_app.logger.info(f"No IBM Dashboard Setting with ID {setting['id']}")
            return Response(status=404)

        dashboard_setting.pin_status = setting['pin_status']
        doosradb.session.commit()
        dashboard_settings_list.append(dashboard_setting.to_json())

    return Response(json.dumps(dashboard_settings_list), status=201, mimetype="application/json")
