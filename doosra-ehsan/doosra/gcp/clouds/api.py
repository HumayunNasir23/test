import json
import os

import flask
import google_auth_oauthlib.flow
from flask import current_app, jsonify, Response, render_template, request

from config import config
from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.gcp.clouds import gcp_clouds
from doosra.gcp.clouds.consts import *
from doosra.gcp.clouds.schemas import *
from doosra.gcp.clouds.utils import check_cloud_exists
from doosra.models import GcpCloud, GcpCloudProject, GCPCredentials, GcpTask
from doosra.validate_json import validate_json


@gcp_clouds.route('/clouds', methods=['POST'])
@validate_json(gcp_cloud_account_schema)
@authenticate
def add_gcp_cloud_account(user_id, user):
    """Add cloud account"""

    data = request.get_json(force=True)

    if check_cloud_exists(data, user.project.id):
        current_app.logger.info("Account already added")
        return Response(status=409)

    cloud_account = GcpCloud(data["name"], user.project.id)
    doosradb.session.add(cloud_account)
    doosradb.session.commit()

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(config['default'].CLIENT_SECRETS_FILE,
                                                                   scopes=config['default'].SCOPES)
    flow.redirect_uri = "{0}v1/gcp/clouds/gcp_oauth_callback".format(os.environ.get('GOOGLE_OAUTH_LINK'))
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=cloud_account.id)

    resp = cloud_account.to_json()
    resp["redirect_url"] = authorization_url
    resp["cloud_id"] = cloud_account.id
    return jsonify(resp)


@gcp_clouds.route('/clouds/<cloud_id>/reauthorize', methods=['POST'])
@authenticate
def reauthorize_gcp_cloud_account(user_id, user, cloud_id):
    """Reauthorize cloud account"""

    cloud_account = doosradb.session.query(GcpCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not cloud_account:
        current_app.logger.info(
            "No GOOGLE cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(config['default'].CLIENT_SECRETS_FILE,
                                                                   scopes=config['default'].SCOPES)
    flow.redirect_uri = "{0}v1/gcp/clouds/gcp_oauth_callback".format(os.environ.get('GOOGLE_OAUTH_LINK'))
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=cloud_account.id)

    resp = cloud_account.to_json()
    resp["redirect_url"] = authorization_url
    resp["cloud_id"] = cloud_account.id
    return jsonify(resp)


@gcp_clouds.route('/clouds/gcp_oauth_callback', methods=['GET'])
def gcp_oauth_callback():
    """Handle callback for authentication from GCP server"""

    if request.args.get('error'):
        current_app.logger.info("Access denied for GCP Cloud account")
        return Response(ACCESS_DENIED, status=400)

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(config['default'].CLIENT_SECRETS_FILE,
                                                                   scopes=config['default'].SCOPES)
    flow.redirect_uri = "{0}v1/gcp/clouds/gcp_oauth_callback".format(os.environ.get('GOOGLE_OAUTH_LINK'))
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    cloud = doosradb.session.query(GcpCloud).filter_by(id=request.args.get('state')).first()
    if cloud:
        cloud.status = "VALID"
        gcp_credentials = GCPCredentials(flow.credentials)
        doosradb.session.add(gcp_credentials)
        cloud.gcp_credentials = gcp_credentials
        doosradb.session.commit()

    return render_template('gcp/success.html')


@gcp_clouds.route('/clouds/<cloud_id>', methods=['DELETE'])
@authenticate
def delete_gcp_cloud_account(user_id, user, cloud_id):
    """Delete a Doosra project's Cloud account"""

    from doosra.tasks import task_revoke_cloud_access

    gcp_cloud_account = doosradb.session.query(GcpCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not gcp_cloud_account:
        current_app.logger.info("No GOOGLE Cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    task = GcpTask(task_revoke_cloud_access.delay(gcp_cloud_account.id).id, "CLOUD", "DELETE", gcp_cloud_account.id,
                   gcp_cloud_account.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_clouds.route('/clouds/tasks/<task_id>', methods=['GET'])
@authenticate
def get_task_details(user_id, user, task_id):
    """
    Get task details for a task using its task_id
    """
    task = doosradb.session.query(GcpTask).filter_by(id=task_id).first()
    if not task:
        current_app.logger.info("No GCP VPC task exists with this id {}".format(task_id))
        return Response(status=404)

    return jsonify(task.to_json())


@gcp_clouds.route('/clouds', methods=['GET'])
@authenticate
def list_gcp_cloud_accounts(user_id, user):
    """List a Doosra project's GCP Cloud Accounts"""

    cloud_accounts = doosradb.session.query(GcpCloud).filter_by(project_id=user.project.id).all()
    if not cloud_accounts:
        return Response(status=204)

    cloud_integrations = list()
    for cloud_account in cloud_accounts:
        cloud_integrations.append(cloud_account.to_json())

    return Response(json.dumps(cloud_integrations), mimetype='application/json')


@gcp_clouds.route('/clouds/<cloud_id>', methods=['GET'])
@authenticate
def get_gcp_cloud_account(user_id, user, cloud_id):
    """List a Doosra project's GCP Cloud Accounts"""

    cloud_account = doosradb.session.query(GcpCloud).filter_by(project_id=user.project.id, id=cloud_id).first()
    if not cloud_account:
        return Response(status=204)
    return Response(json.dumps(cloud_account.to_json()), mimetype='application/json')


@gcp_clouds.route('/clouds/<cloud_id>', methods=['PATCH'])
@authenticate
@validate_json(gcp_cloud_update_schema)
def update_gcp_cloud_account(user_id, user, cloud_id):
    """Update a DOOSRA project's cloud account"""

    data = request.get_json(force=True)

    cloud_account = doosradb.session.query(GcpCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not cloud_account:
        current_app.logger.info("No Google loud account found with ID {}".format(cloud_id))
        return Response(status=404)

    if data.get("name") != "" and data.get("name") != cloud_account.name:
        if check_cloud_exists(data, user.project.id):
            current_app.logger.info("Google Account with same name already added")
            return Response(status=409)

        cloud_account.name = data["name"]
        doosradb.session.commit()

    return jsonify(cloud_account.to_json())


@gcp_clouds.route('/clouds/<cloud_id>/sync', methods=['POST'])
@authenticate
def sync_cloud(user_id, user, cloud_id):
    """Sync cloud devices
    :Args:
        user_id (str): ID of user.
    :Return:
        { 'status': <String> }
    """
    from doosra.tasks.other.gcp_tasks import sync_cloud

    cloud_account = doosradb.session.query(GcpCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not cloud_account:
        return Response(status=404)

    sync_task = cloud_account.gcp_tasks.filter_by(type="CLOUD", action="SYNC").first()
    if sync_task and sync_task.status == CREATED and not request.args.get('force'):
        return Response(status=202)
    elif sync_task:
        doosradb.session.delete(sync_task)

    sync_task = GcpTask(sync_cloud.delay(cloud_id).id, "CLOUD", "SYNC", cloud_id, cloud_account.id)
    doosradb.session.add(sync_task)
    doosradb.session.commit()

    return Response(status=202)


@gcp_clouds.route('/clouds/<cloud_id>/sync', methods=['GET'])
@authenticate
def show_sync_status(user_id, user, cloud_id):
    """Show status of the sync process
    :Args:
        user_id (str): ID of user.
    :Return:
        { 'status': <String> }
    """

    cloud_account = doosradb.session.query(GcpCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not cloud_account:
        return Response(status=404)

    sync_task = cloud_account.gcp_tasks.filter_by(type="CLOUD", action="SYNC").first()
    if not sync_task:
        return jsonify({"status": SUCCESS})

    return jsonify(sync_task.to_json())


@gcp_clouds.route('/clouds/<cloud_id>/cloud_projects', methods=['GET'])
@authenticate
def list_cloud_projects(user_id, user, cloud_id):
    """
    Get cloud projects related with a cloud account
    """
    cloud = doosradb.session.query(GcpCloud).filter_by(id=cloud_id, project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No GCP cloud account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    projects_list = list()
    for project in cloud.gcp_cloud_projects.all():
        projects_list.append(project.to_json())

    if not projects_list:
        return Response(status=204)

    return Response(json.dumps(projects_list), mimetype='application/json')


@gcp_clouds.route('/clouds/<cloud_id>/cloud_projects/<cloud_project_id>', methods=['GET'])
@authenticate
def get_cloud_project(user_id, user, cloud_id, cloud_project_id):
    """
    Get cloud_project related with a cloud account
    """
    cloud_project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id, cloud_id=cloud_id).first()
    if not cloud_project:
        current_app.logger.info("No GCP cloud project account found with ID {cloud_id}".format(cloud_id=cloud_id))
        return Response(status=404)

    if not cloud_project:
        return Response(status=204)

    return Response(json.dumps(cloud_project.to_json()), mimetype='application/json')
