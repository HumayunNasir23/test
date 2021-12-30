import json

from flask import jsonify, request, Response, current_app
from sqlalchemy import or_

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import CREATED, SUCCESS
from doosra.common.utils import decrypt_api_key
from doosra.models import SoftlayerCloud, SyncTask
from doosra.softlayer import softlayer
from doosra.softlayer.schemas import *
from doosra.validate_json import validate_json


@softlayer.route("/clouds", methods=["POST"])
@validate_json(softlayer_account_schema)
@authenticate
def add_softlayer_cloud_account(user_id, user):
    """
    Add Softlayer Cloud Account
    :param user_id:
    :param user:
    :return:
    """
    from doosra.tasks.other.softlayer_tasks import task_validate_softlayer_cloud

    data = request.get_json(force=True)
    existing_softlayer_account = doosradb.session.query(SoftlayerCloud).filter(
        SoftlayerCloud.project_id == user.project.id,
        or_(SoftlayerCloud.name == data['name']), SoftlayerCloud.username == data['username']).first()

    if existing_softlayer_account:
        return Response("ERROR_SAME_NAME", status=409)

    softlayer_cloud_account = SoftlayerCloud(
        name=data['name'], username=data['username'], api_key=data['api_key'],
        ibm_cloud_account_id=data['ibm_cloud_account_id'],
        project_id=user.project.id
    )
    doosradb.session.add(softlayer_cloud_account)
    doosradb.session.commit()

    task_validate_softlayer_cloud.apply_async(queue='sync_queue', args=[softlayer_cloud_account.id])
    return Response(json.dumps(softlayer_cloud_account.to_json()), status=201, mimetype="application/json")


@softlayer.route("/clouds", methods=["GET"])
@authenticate
def get_all_softlayer_cloud_accounts(user_id, user):
    """
    Get All Softlayer Clound Accounts Associated with a Project
    :param user_id:
    :param user:
    :return:
    """
    softlayer_cloud_accounts = doosradb.session.query(SoftlayerCloud).filter_by(project_id=user.project.id).all()
    if not softlayer_cloud_accounts:
        current_app.logger.info("No Softlayer Cloud account found for user with ID {user_id}".format(user_id=user.id))
        return Response(status=204)

    softlayer_cloud_accounts_list = []
    for softlayer_cloud_account in softlayer_cloud_accounts:
        softlayer_cloud_accounts_list.append(softlayer_cloud_account.to_json())

    return Response(response=json.dumps(softlayer_cloud_accounts_list), status=200, mimetype="application/json")


@softlayer.route("/clouds/<softlayer_cloud_account_id>", methods=["GET"])
@authenticate
def get_softlayer_cloud_account(user_id, user, softlayer_cloud_account_id):
    """
    Get Softlayer Cloud Account Provided Its Id
    :param user_id:
    :param user:
    :return:
    """
    softlayer_cloud_account = doosradb.session.query(SoftlayerCloud).filter_by(project_id=user.project.id,
                                                                               id=softlayer_cloud_account_id).first()
    if not softlayer_cloud_account:
        current_app.logger.info("No Softlayer Cloud account found with ID {id}".format(id=softlayer_cloud_account_id))
        return Response(status=204)

    return Response(response=json.dumps(softlayer_cloud_account.to_json()), status=200, mimetype="application/json")


@softlayer.route("/clouds/<softlayer_cloud_account_id>", methods=["PUT", "PATCH"])
@validate_json(softlayer_account_update_schema)
@authenticate
def update_softlayer_cloud_account(user_id, user, softlayer_cloud_account_id):
    """
    Update Softlayer Cloud Account
    :param user_id:
    :param user:
    :param softlayer_cloud_account_id:
    :return:
    """
    from doosra.tasks.other.softlayer_tasks import task_validate_softlayer_cloud

    data = request.get_json(force=True)
    softlayer_cloud_account = doosradb.session.query(SoftlayerCloud).filter_by(project_id=user.project.id,
                                                                               id=softlayer_cloud_account_id).first()
    if not softlayer_cloud_account:
        current_app.logger.info("No Softlayer Cloud account found with ID {id}".format(id=softlayer_cloud_account_id))
        return Response(status=204)

    if not softlayer_cloud_account.ibm_cloud_account_id:
        if data.get("ibm_cloud_account_id"):
            softlayer_cloud_account.ibm_cloud_account_id = data.get("ibm_cloud_account_id")

    if data.get("name") and data["name"] != softlayer_cloud_account.name:
        existing_softlayer_account = doosradb.session.query(SoftlayerCloud).filter_by(
            name=data["name"], project_id=user.project.id).first()
        if existing_softlayer_account:
            return Response("ERROR_SAME_NAME", status=409)

        softlayer_cloud_account.name = data["name"]

    if data.get("username") and data["username"] != softlayer_cloud_account.username:
        existing_softlayer_account = doosradb.session.query(SoftlayerCloud).filter_by(
            username=data["username"], project_id=user.project.id).first()
        if existing_softlayer_account:
            return Response("ERROR_SAME_USERNAME", status=409)

        softlayer_cloud_account.username = data["username"]

    if data.get("ibm_cloud_account_id") and data["ibm_cloud_account_id"] != \
            softlayer_cloud_account.ibm_cloud_account_id:
        softlayer_cloud_account.ibm_cloud_account_id = data["ibm_cloud_account_id"]

    if data.get("api_key") and data["api_key"] != decrypt_api_key(softlayer_cloud_account.api_key):
        softlayer_cloud_account.api_key = data["api_key"]

    softlayer_cloud_account.status = "AUTHENTICATING"
    doosradb.session.commit()
    task_validate_softlayer_cloud.apply_async(queue='sync_queue', args=[softlayer_cloud_account.id])
    return Response(json.dumps(softlayer_cloud_account.to_json()), status=200, mimetype="application/json")


@softlayer.route("/clouds/<softlayer_cloud_account_id>", methods=["DELETE"])
@authenticate
def delete_softlayer_cloud_account(user_id, user, softlayer_cloud_account_id):
    """
    Delete Softlayer Cloud Accounts
    :param user_id:
    :param user:
    :return:
    """
    softlayer_cloud_account = doosradb.session.query(SoftlayerCloud).filter_by(project_id=user.project.id,
                                                                               id=softlayer_cloud_account_id).first()
    if not softlayer_cloud_account:
        current_app.logger.info("No Softlayer Cloud account found with ID {id}".format(id=softlayer_cloud_account_id))
        return Response(status=204)

    doosradb.session.delete(softlayer_cloud_account)
    doosradb.session.commit()
    return Response(status=204)


@softlayer.route("/clouds-images", methods=["POST"])
@authenticate
def sync_softlayer_cloud_accounts_images(user_id, user):
    """
    Initiate sync softlayer cloud account images for for SL cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.softlayer_tasks import task_get_softlayer_cloud_images

    softlayer_cloud_accounts = doosradb.session.query(SoftlayerCloud).filter_by(
        project_id=user.project.id, status='VALID').all()

    if not softlayer_cloud_accounts:
        current_app.logger.info("No Softlayer Cloud account found for user with ID '{user_id}'".format(user_id=user.id))
        return Response(status=204)

    sync_task = user.project.sync_tasks.filter(SyncTask.type == "IMAGE", SyncTask.cloud_type == "SOFTLAYER").first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = SyncTask("SOFTLAYER", "IMAGE", user.project.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_softlayer_cloud_images.apply_async(queue='sync_queue', args=[task.id, user.project.id])
    return Response(status=202)


@softlayer.route("/clouds-images", methods=["GET"])
@authenticate
def get_all_softlayer_cloud_accounts_images(user_id, user):
    """
    Get All Softlayer Clound Account instances Associated with a Project
    :return:
    """
    if not user.project:
        current_app.logger.info("No Project found with ID {user_id}".format(user_id=user_id))
        return Response(status=404)

    task = user.project.sync_tasks.filter(SyncTask.type == "IMAGE", SyncTask.cloud_type == "SOFTLAYER").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify(task.result if task.result else {})


@softlayer.route("/clouds-instances", methods=["POST"])
@authenticate
def sync_task_list_softlayer_instance_hostnames(user_id, user):
    """
    Initiate sync softlayer cloud account VSI's for for SL cloud account.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.softlayer_tasks import task_list_softlayer_instance_hostnames

    softlayer_cloud_accounts = doosradb.session.query(SoftlayerCloud).filter_by(
        project_id=user.project.id, status='VALID').all()

    if not softlayer_cloud_accounts:
        current_app.logger.info("No Softlayer Cloud account found for user with ID '{user_id}'".format(user_id=user.id))
        return Response(status=204)

    sync_task = user.project.sync_tasks.filter(SyncTask.type == "INSTANCE", SyncTask.cloud_type == "SOFTLAYER").first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = SyncTask("SOFTLAYER", "INSTANCE", user.project.id)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_list_softlayer_instance_hostnames.apply_async(queue='sync_queue', args=[task.id, user.project.id])
    return Response(status=202)


@softlayer.route("/clouds-instances", methods=["GET"])
@authenticate
def list_softlayer_instance_hostnames(user_id, user):
    """
    Get All Softlayer Clound Account instance Hostnames Associated with a Project
    :return:
    """
    if not user.project:
        current_app.logger.info("No Project found with ID {user_id}".format(user_id=user_id))
        return Response(status=404)

    task = user.project.sync_tasks.filter(SyncTask.type == "INSTANCE", SyncTask.cloud_type == "SOFTLAYER").first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify(task.result if task.result else {})


@softlayer.route("/clouds-instances/<instance_id>", methods=["POST"])
@authenticate
def sync_get_classical_instance_details(user_id, user, instance_id):
    """
    Initiate sync for VSI Detail.
    If there is already a sync in progress, return same task's status.
    :return:
    """
    from doosra.tasks.other.softlayer_tasks import task_get_classical_instance_details

    softlayer_cloud_accounts = doosradb.session.query(SoftlayerCloud).filter_by(
        project_id=user.project.id, status='VALID').all()

    if not softlayer_cloud_accounts:
        current_app.logger.info("No Softlayer Cloud account found for user with ID '{user_id}'".format(user_id=user.id))
        return Response(status=204)

    sync_task = user.project.sync_tasks.filter(SyncTask.type == "INSTANCE", SyncTask.cloud_type == "SOFTLAYER",
                                               SyncTask.resource_id == instance_id).first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    task = SyncTask("SOFTLAYER", "INSTANCE", user.project.id, instance_id)
    doosradb.session.add(task)
    doosradb.session.commit()
    task_get_classical_instance_details.apply_async(queue='sync_queue', args=[task.id, user.project.id, instance_id])
    return Response(status=202)


@softlayer.route("/clouds-instances/<instance_id>", methods=["GET"])
@authenticate
def get_classical_instance_details(user_id, user, instance_id):
    if not user.project:
        current_app.logger.info("No Project found with ID {user_id}".format(user_id=user_id))
        return Response(status=404)

    task = user.project.sync_tasks.filter(SyncTask.type == "INSTANCE", SyncTask.cloud_type == "SOFTLAYER",
                                          SyncTask.resource_id == instance_id).first()
    if not task:
        return Response("TASK_NOT_FOUND", status=404)

    if task.status != SUCCESS:
        return jsonify({"status": task.status})

    return jsonify(task.result if task.result else {})
