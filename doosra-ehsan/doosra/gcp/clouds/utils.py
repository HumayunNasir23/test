from datetime import datetime

from flask import current_app

from doosra import db as doosradb
from doosra.common.retry import make_request
from doosra.gcp.clouds.consts import INVALID
from doosra.gcp.managers.exceptions import *
from doosra.gcp.managers.gcp_manager import GCPManager
from doosra.models import GcpCloud, GcpCloudProject


def check_cloud_exists(data, project_id):
    """
    Check if cloud with same name exists across the project and return if it exists
    """
    cloud_account = doosradb.session.query(GcpCloud).filter_by(name=data["name"], project_id=project_id).first()
    return cloud_account is not None


def revoke_cloud_access(token):
    """
    This method revokes cloud access from a user's Google account, so we are no longer able to make
    requests on user's behalf.
    """
    if token:
        response = make_request(method="POST",
                                params={'token': token},
                                url="https://accounts.google.com/o/oauth2/revoke",
                                headers={'content-type': 'application/x-www-form-urlencoded'})
        if response and response.status_code != 200:
            current_app.logger.debug("ERROR revoking token: response.status_code: {}".format(response.status_code))
            return
    return True


def sync_gcp_cloud_account(cloud_id):
    """
    Sync GCP projects, get current projects from Google, and sync it with database
    :param cloud_id:
    :return:
    """
    cloud_account = doosradb.session.query(GcpCloud).filter_by(id=cloud_id).first()
    if not cloud_account:
        return
    try:
        gcp_manager = GCPManager(cloud_account)
        projects = gcp_manager.resource_management_operations.fetch_ops.get_cloud_projects()
        for project in projects:
            project_to_add = project.make_copy()
            project_to_add.user_project_id = cloud_account.project_id
            existing_project = doosradb.session.query(GcpCloudProject).filter_by(
                name=project.name, cloud_id=cloud_account.id).first()
            project_to_add.add_update_db(existing_project)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_account.status = INVALID
            doosradb.session.commit()
    else:
        cloud_account.last_synced_at = datetime.utcnow()
        doosradb.session.commit()
        current_app.logger.info("Sync successful for GCP Cloud {}".format(cloud_account.id))
        return True
