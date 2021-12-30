import os

from flask import Response, jsonify, request, current_app

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.migration import migration
from doosra.migration.consts import VPC_MIGRATE
from doosra.migration.managers.softlayer_manager import SoftLayerManager
from doosra.migration.models import CMModels
from doosra.migration.schema import add_content_migration_meta_data_schema, start_nas_migration_schema
from doosra.models import SoftlayerCloud, User, IBMCloud
from doosra.models.migration_models import MigrationTask
from doosra.validate_json import validate_json


@migration.route('/migrate/tasks/<task_id>', methods=['GET'])
@authenticate
def get_migration_task_details(user_id, user, task_id):
    """
    Get Migration Task details
    :return:
    """
    migration_task = doosradb.session.query(MigrationTask).filter_by(id=task_id).first()
    if not migration_task:
        return Response(status=404)

    resp = jsonify(migration_task.to_json())
    resp.status_code = 200
    return resp


@migration.route('/migrate/vpcs', methods=['POST'])
@authenticate
def migrate_vpc(user_id, user):
    """
    Migrate VYATTA-5600 config file to VPC schema
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.migration_tasks import task_migrate_vpc

    softlayer_cloud_id = request.form.get("softlayer_cloud_id")
    config_file = request.files.get('config_file')

    if not (config_file or softlayer_cloud_id):
        current_app.logger.info(
            "No Config File or SoftLayer Cloud specified for Migration with user id {id}".format(id=user_id))
        return Response(status=400)

    configs, softlayer_cloud = None, None
    if config_file:
        if not config_file.filename.lower().endswith('.txt'):
            return Response("FILE_FORMAT_NOT_SUPPORTED", status=422)

        configs = config_file.read()
        if not configs:
            return Response("EMPTY_FILE_DETECTED", status=422)

        configs = configs.decode('utf-8')

    if softlayer_cloud_id:
        softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(id=softlayer_cloud_id).first()
        if not softlayer_cloud:
            return Response("SOFTLAYER_CLOUD_NOT_FOUND", status=400)

        if not softlayer_cloud.ibm_cloud_account_id:
            return Response("Reference of IBM Cloud VPC Account Not Found. Please Update your IBM Cloud Classic Account"
                            , status=404)
        ibm_cloud_account = doosradb.session.query(IBMCloud).filter_by(id=softlayer_cloud.ibm_cloud_account_id).first()
        if not ibm_cloud_account:
            return Response("IBM_CLOUD_VPC_ACCOUNT_NOT_FOUND", status=404)

        elif ibm_cloud_account.status == "INVALID":
            return Response("INVALID_IBM_CLOUD_VPC_ACCOUNT", status=422)

        elif ibm_cloud_account.status == "AUTHENTICATING":
            return Response("AUTHENTICATING_IBM_CLOUD_VPC_ACCOUNT", status=422)

    migration_task = MigrationTask(user.project.id)
    doosradb.session.add(migration_task)
    doosradb.session.commit()

    if softlayer_cloud:
        task_migrate_vpc.apply_async(
            kwargs={'task_id': migration_task.id, 'configs': configs, 'user_name': softlayer_cloud.username,
                    'api_key': softlayer_cloud.api_key}, queue='sync_queue')
    else:
        task_migrate_vpc.apply_async(
            kwargs={'task_id': migration_task.id, 'configs': configs, 'user_name': None, 'api_key': None},
            queue='sync_queue')

    current_app.logger.info(VPC_MIGRATE.format(user.email))
    resp = jsonify({"task_id": migration_task.id})
    resp.status_code = 202
    return resp


@migration.route('/migrate/content', methods=['POST'])
@validate_json(add_content_migration_meta_data_schema)
def migrate_content():
    """task_add_content_migration_meta_data
    Save Block Volume and File Storage in Doosradb in CMModel for the sake of NAS migration
    """

    from doosra.tasks.other.migration_tasks import task_add_content_migration_meta_data

    data = request.get_json(force=True)
    user = User.query.get(data["user_id"])
    if not user:
        return Response("USER_NOT_FOUND", status=400)
    task_add_content_migration_meta_data(user_id=user.id, data=data)
    return Response(status=200)


@migration.route('/migrate/content/<vsi_id>', methods=['GET'])
@authenticate
def get_content_meta_data(user_id, user, vsi_id):
    """
    Get File Storage and Block Volume Data against VSI Classic ID
    """
    content_data = CMModels.query.get(vsi_id)
    if not content_data:
        return Response(status=204)
    resp = jsonify(content_data.to_json())
    resp.status_code = 200
    return resp


@migration.route('/migrate/content/start/<user_id>', methods=['PATCH'])
@validate_json(start_nas_migration_schema)
def start_content_migration(user_id):
    """
    Start NAS Migration with the following three apis
    1): Get IDs of the locations by searching with names
    2): Create a Migration Object
    3): Start Moving the contents for this specific migration object
    """
    from doosra.tasks import task_start_nas_migration
    data = request.get_json(force=True)
    user = User.query.get(user_id)
    if not user:
        return Response("USER_NOT_FOUND", status=404)
    db_migration_api_key = os.environ.get('DB_MIGRATION_API_KEY')
    db_migration_controller_host = os.environ.get('DB_MIGRATION_CONTROLLER_HOST')
    task_start_nas_migration.si(
        data=data, db_migration_controller_host=db_migration_controller_host,
        db_migration_api_key=db_migration_api_key,
        user_id=user_id).delay()

    return Response(status=202)
