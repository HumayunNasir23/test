from flask import current_app

from doosra import db as doosradb
from doosra.gcp.clouds.consts import INVALID
from doosra.gcp.managers.exceptions import CloudAuthError, CloudExecuteError, CloudInvalidRequestError
from doosra.gcp.managers.gcp_manager import GCPManager
from doosra.models.gcp_models import GcpCloudProject


def get_regions(project_id):
    """
    Get latest regions from cloud account
    :param project_id:
    :return:
    """
    cloud_project = doosradb.session.query(GcpCloudProject).filter_by(id=project_id).first()
    if not cloud_project:
        return
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        regions_list = gcp_manager.compute_engine_operations.fetch_ops.get_regions(cloud_project.project_id)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return regions_list


def get_zones(project_id):
    """
    Get latest zones from cloud account
    :return:
    """
    cloud_project = doosradb.session.query(GcpCloudProject).filter_by(id=project_id).first()
    if not cloud_project:
        return

    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        zones_list = gcp_manager.compute_engine_operations.fetch_ops.get_zones(cloud_project.project_id)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return zones_list


def get_images(project_id):
    """
    Get latest images from cloud account
    :return:
    """
    cloud_project = doosradb.session.query(GcpCloudProject).filter_by(id=project_id).first()
    if not cloud_project:
        return

    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        images_list = gcp_manager.compute_engine_operations.fetch_ops.get_all_images(cloud_project.project_id)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return images_list


def get_machine_types(project_id):
    """
    Get latest machine types from cloud account
    :return:
    """
    cloud_project = doosradb.session.query(GcpCloudProject).filter_by(id=project_id).first()
    if not cloud_project:
        return

    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        machine_types_list = gcp_manager.compute_engine_operations.fetch_ops.get_machine_types(cloud_project.project_id)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return machine_types_list
