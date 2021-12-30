from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, ERROR_CREATING, ERROR_DELETING, DELETING, DELETED
from doosra.gcp.clouds.consts import INVALID
from doosra.gcp.managers.exceptions import *
from doosra.gcp.managers.gcp_manager import GCPManager
from doosra.models.gcp_models import GcpInstance, GcpInstanceGroup, GcpVpcNetwork


def deploy_instance_group(cloud_project, instance_group_name, data):
    """
    Create and deploy instance group on Google Cloud Platform
    :return:
    """
    objs_to_configure, gcp_instance_group = list(), None
    current_app.logger.info("Deploying Instance Group '{name}' on GCP cloud project '{project}'".format(
        name=instance_group_name, project=cloud_project.name))
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        instance_groups = gcp_manager.compute_engine_operations.fetch_ops.get_all_instance_groups(
            cloud_project.project_id, name=instance_group_name)
        if instance_groups:
            raise CloudInvalidRequestError(
                "GcpInstanceGroup with name '{}' already configured on GCP cloud".format(instance_group_name))

        vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=data['vpc_id']).first()
        if not vpc:
            raise CloudInvalidRequestError("VPC with ID {} not found".format(data['vpc_id']))

        vpc_networks = gcp_manager.compute_engine_operations.fetch_ops.get_vpc_networks(
            cloud_project.project_id, name=vpc.name)
        if not vpc_networks:
            raise CloudInvalidRequestError("VPC network with name '{}' not found".format(vpc.name))

        gcp_instance_group = GcpInstanceGroup(instance_group_name, data.get('zone'), data.get('description'))
        gcp_instance_group.gcp_vpc_network = vpc
        if data.get('instances'):
            for instance in data.get('instances'):
                gcp_instance = doosradb.session.query(GcpInstance).filter_by(id=instance['instance_id']).first()
                if not gcp_instance:
                    raise CloudInvalidRequestError("GCP Instance with ID {} not found".format(instance['instance_id']))

                existing_instance = gcp_manager.compute_engine_operations.fetch_ops.get_instances(
                    cloud_project.project_id, gcp_instance.zone)
                if not existing_instance:
                    raise CloudInvalidRequestError("GCP Instance with name {} not found".format(gcp_instance.name))
                gcp_instance_group.instances.append(gcp_instance)

        doosradb.session.add(gcp_instance_group)
        doosradb.session.commit()
        gcp_manager.compute_engine_operations.push_obj_confs(gcp_instance_group, cloud_project.project_id)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
        if gcp_instance_group:
            gcp_instance_group.status = ERROR_CREATING
        doosradb.session.commit()
        return None, ex.msg
    else:
        gcp_instance_group.status = CREATED
        doosradb.session.commit()
        return gcp_instance_group, None


def delete_instance_group(instance_group):
    """
    Delete instance group from GCP Cloud Project
    :return:
    """
    cloud_project = instance_group.gcp_vpc_network.gcp_cloud_project
    current_app.logger.info("Deleting GCP Instance '{name}' on cloud project '{project}'".format(
        name=instance_group.name, project=cloud_project.name))
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        existing_instance_group = gcp_manager.compute_engine_operations.fetch_ops.get_instance_groups(
            cloud_project.project_id, name=instance_group.name, zone=instance_group.zone)
        if existing_instance_group:
            gcp_manager.compute_engine_operations.push_obj_confs(instance_group, cloud_project.project_id, delete=True)
        instance_group.status = DELETING
        doosradb.session.commit()
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
        instance_group.status = ERROR_DELETING
        doosradb.session.commit()
        return False, ex.msg
    else:
        instance_group.status = DELETED
        doosradb.session.delete(instance_group)
        doosradb.session.commit()
        return True, None
