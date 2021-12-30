import json
import logging

from flask import jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.ibm.common.consts import INST_START
from doosra.ibm.instances import ibm_instances
from doosra.ibm.instances.consts import *
from doosra.ibm.instances.schemas import *
from doosra.models import IBMCloud, IBMInstance, IBMSecurityGroup, IBMSubnet, IBMTask, IBMVpcNetwork, \
    IBMInstanceProfile, IBMImage, IBMInstanceTasks
from doosra.models.migration_models import SecondaryVolumeMigrationTask
from doosra.validate_json import validate_json

LOGGER = logging.getLogger(__name__)


@ibm_instances.route('/instances', methods=['POST'])
@validate_json(ibm_instance_schema)
@authenticate
def add_ibm_instance(user_id, user):
    """
    Add IBM Instance
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.instance_tasks import task_create_ibm_instance_workflow

    data = request.get_json(force=True)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        LOGGER.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=data["vpc_id"], cloud_id=data["cloud_id"]).first()
    if not vpc:
        LOGGER.info("No IBM VPC found with ID {id}".format(id=data['vpc_id']))
        return Response(status=404)

    instance = doosradb.session.query(IBMInstance).filter_by(name=data['name'], cloud_id=data['cloud_id'],
                                                             region=vpc.region).first()
    if instance:
        return Response("ERROR_CONFLICTING_INSTANCE_NAME", status=409)

    if data.get('network_interfaces'):
        for interface in data['network_interfaces']:
            subnet = doosradb.session.query(IBMSubnet).filter_by(id=interface['subnet_id']).first()
            if not subnet:
                LOGGER.info(f"No IBM SUBNET found with ID {interface['subnet_id']}")
                return Response(f"NO SUBNET FOUND WITH `{interface['subnet_id']}` ID", status=404)

            security_groups = list(
                map(lambda security_group_: doosradb.session.query(IBMSecurityGroup).filter_by(
                    id=security_group_).first(), interface['security_groups']))

            security_group_found = all(map(lambda obj: isinstance(obj, IBMSecurityGroup), security_groups))

            if not security_group_found:
                LOGGER.info("NO SECURITY GROUP FOUND")
                return Response(f"NO SECURITY GROUP FOUND", status=404)

    if data.get("dedicated_host_name"):
        ibm_dedicated_host = \
            cloud.dedicated_hosts.filter_by(name=data["dedicated_host_name"], region=vpc.region).first()
        if not ibm_dedicated_host:
            return Response(
                f"Dedicated host '{data['dedicated_host_name']}' not found in region {vpc.region}", status=404
            )
        if not ibm_dedicated_host.instance_placement_enabled:
            return Response(
                f"Dedicated host '{data['dedicated_host_name']}' instance placement is disabled", status=400
            )

    elif data.get("dedicated_host_group_name"):
        ibm_dedicated_host_group = \
            cloud.dedicated_host_groups.filter_by(name=data["dedicated_host_group_name"], region=vpc.region).first()
        if not ibm_dedicated_host_group:
            return Response(
                f"Dedicated host group '{data['dedicated_host_group_name']}' not found in region {vpc.region}",
                status=404
            )

        if not ibm_dedicated_host_group.dedicated_hosts.filter_by(instance_placement_enabled=True).count():
            return Response(
                f"All dedicated hosts in group '{data['dedicated_host_group_name']}' have instance placement disabled",
                status=400
            )

    ibm_instance = IBMInstance(
        name=data.get("name"),
        zone=data["zone"],
        user_data=data.get("user_data"),
        cloud_id=vpc.ibm_cloud.id,
        state=INST_START,
        region=vpc.region,
        is_volume_migration=data.get("data_migration")
    )
    ibm_instance_profile = IBMInstanceProfile(name=data["instance_profile"], cloud_id=vpc.ibm_cloud.id)
    ibm_instance_profile = ibm_instance_profile.get_existing_from_db() or ibm_instance_profile
    ibm_instance.ibm_instance_profile = ibm_instance_profile.make_copy()
    ibm_instance.ibm_resource_group = vpc.ibm_resource_group.make_copy()
    ibm_instance = ibm_instance.make_copy().add_update_db(vpc)
    ibm_instance_id = ibm_instance.id

    ibm_instance = ibm_instance.make_copy()
    ibm_image = None
    if data['image'].get('image_location') in {IBMInstanceTasks.LOCATION_CLASSICAL_VSI,
                                               IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE,
                                               IBMInstanceTasks.LOCATION_COS_VHD,
                                               IBMInstanceTasks.LOCATION_COS_VMDK,
                                               IBMInstanceTasks.LOCATION_COS_QCOW2,
                                               }:
        ibm_image = IBMImage(name=ibm_instance.name, region=vpc.region, cloud_id=vpc.ibm_cloud.id, visibility="private")

    elif data['image'].get('image_location') == IBMInstanceTasks.LOCATION_CUSTOM_IMAGE:
        ibm_image = IBMImage(name=data['image'].get('custom_image'), region=vpc.region, cloud_id=vpc.ibm_cloud.id,
                             visibility="private")

    elif data['image'].get('image_location') == IBMInstanceTasks.LOCATION_PUBLIC_IMAGE:
        ibm_image = IBMImage(name=data['image'].get('public_image'), region=vpc.region, cloud_id=vpc.ibm_cloud.id,
                             visibility="public")
    ibm_image.ibm_resource_group = vpc.ibm_resource_group.make_copy()
    existing_image = ibm_image.get_existing_from_db()
    if existing_image:
        existing_image = existing_image.make_copy()
    ibm_instance.ibm_image = existing_image or ibm_image
    ibm_instance = ibm_instance.add_update_db(vpc)

    task = IBMTask(
        task_id=None, type_="INSTANCE", region=vpc.region, action="ADD", cloud_id=vpc.ibm_cloud.id,
        resource_id=ibm_instance.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    task_create_ibm_instance_workflow.delay(
        task_id=task.id, cloud_id=vpc.ibm_cloud.id, region=vpc.region, instance_data=data, instance_id=ibm_instance_id)

    LOGGER.info(INSTANCE_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id,
                    "resource_id": ibm_instance.id})
    resp.status_code = 202
    return resp


@ibm_instances.route('/instances', methods=['GET'])
@authenticate
def list_ibm_instances(user_id, user):
    """
    List all IBM Instances
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        LOGGER.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    instances_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        instances = ibm_cloud.instances.all()
        for instance in instances:
            instances_list.append(instance.to_json())

    if not instances_list:
        return Response(status=204)

    return Response(json.dumps(instances_list), mimetype='application/json')


@ibm_instances.route('/instances/<instance_id>', methods=['GET'])
@authenticate
def get_ibm_instance(user_id, user, instance_id):
    """
    Get IBM Instance
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param instance_id: ID for IBM Instance
    :return: Response object from flask package
    """
    instance = doosradb.session.query(IBMInstance).filter_by(id=instance_id).first()
    if not instance:
        LOGGER.info("No IBM Instance found with ID {id}".format(id=instance_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=instance.cloud_id,
                                                           project_id=user.project.id).first()
    if not ibm_cloud:
        LOGGER.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=instance.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return Response(json.dumps(instance.to_json()), mimetype="application/json")


@ibm_instances.route('/instances/<instance_id>', methods=['DELETE'])
@authenticate
def delete_ibm_instance(user_id, user, instance_id):
    """
    Delete an IBM Instance
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param instance_id: instance ID for IBM Insntace
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.instance_tasks import task_delete_ibm_instance_workflow

    instance = doosradb.session.query(IBMInstance).filter_by(id=instance_id).first()
    if not instance:
        LOGGER.info("No IBM Instance found with ID {id}".format(id=instance_id))
        return Response(status=404)

    if instance.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not instance.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="INSTANCE", region=instance.region, action="DELETE",
        cloud_id=instance.ibm_cloud.id, resource_id=instance.id)

    doosradb.session.add(task)
    instance.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_instance_workflow.delay(task_id=task.id, cloud_id=instance.ibm_cloud.id,
                                            region=instance.region, instance_id=instance.id)

    LOGGER.info(INSTANCE_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_instances.route("/instances/secondary_volume_migration/<secondary_task_id>", methods=["PATCH"])
@validate_json(secondary_volume_migration_schema)
def update_secondary_volume_status(secondary_task_id):
    LOGGER.info("Volume migration is completed deleting the extra resources for secondary task {id}".format(
        id=secondary_task_id))
    """This api is used for keeping track of volume migration once completed request for detaching"""

    from doosra.tasks.ibm.instance_tasks import delete_migration_resources
    secondary_volume_task = (
        doosradb.session.query(SecondaryVolumeMigrationTask)
            .filter_by(id=secondary_task_id)
            .first()
    )
    data = request.get_json(force=True)

    if not secondary_volume_task:
        LOGGER.info(
            "No Secondary Volume Migration Task found with ID {task_id}".format(
                task_id=secondary_task_id
            )
        )
        return Response(status=404)

    if not data:
        LOGGER.info(
            "No data provided to update task status for task {task_id}".format(
                task_id=secondary_volume_task.id
            )
        )
        return Response(status=400)

    if secondary_volume_task.status in {FAILED, SUCCESS}:
        LOGGER.info(
            "Task is already updated of id: {task_id}".format(task_id=secondary_task_id)
        )
        return Response(status=403)

    secondary_volume_task.status = data["status"]
    if data.get("message"):
        secondary_volume_task.message = data["message"]

    if data["status"] in {FAILED, SUCCESS}:
        delete_migration_resources.si(secondary_volume_task_id=secondary_volume_task.id).delay()
        LOGGER.info(
            "Additional Resrouces for instance {instance_id} are removed successfully..".format(
                instance_id=secondary_volume_task.instance_id
            )
        )
    doosradb.session.commit()
    LOGGER.info(
        "'{instance_id}' secondary volume migration task updated..".format(
            instance_id=secondary_volume_task.instance_id
        )
    )
    return Response(status=200)


@ibm_instances.route("/instances/secondary-volume-migration/windows/<secondary_volume_migration_task_id>",
                     methods=["PUT"])
@validate_json(windows_secondary_volume_migration_schema)
def update_svm_report(secondary_volume_migration_task_id):
    """
    Update secondary volume migration report
    """
    from doosra.tasks.ibm.instance_tasks import delete_windows_resources

    task = (
        doosradb.session.query(SecondaryVolumeMigrationTask)
            .filter_by(id=secondary_volume_migration_task_id)
            .first()
    )
    if not task:
        LOGGER.info("No Task found with ID {secondary_volume_migration_task_id}".format(
            secondary_volume_migration_task_id=secondary_volume_migration_task_id))
        return Response(status=404)

    data = request.get_json(force=True)
    if not data:
        LOGGER.info(
            "No data provided to update task status for task {secondary_volume_migration_task_id}".format(
                secondary_volume_migration_task_id=secondary_volume_migration_task_id
            )
        )
        return Response(status=400)

    instance = doosradb.session.query(IBMInstance).filter_by(id=data["instance_id"]).first()
    if not instance:
        LOGGER.info("No Instance found with ID {instance_id}".format(instance_id=instance.id))
        return Response(status=404)

    if instance.id != task.ibm_instance.id:
        LOGGER.info("Task resource_id dont match the payload instance_id".format(instance_id=instance.id))
        return Response(status=404)

    if task.status in {SUCCESS, FAILED}:
        return Response(status=400)

    if data["status"] == IN_PROGRESS and task.status == PENDING:
        task.status = data["status"]
        LOGGER.info(
            "Secondary Volume Migration for Windows is '{status}' for instance '{name}' and ID:'{instance_id}' ".format(
                status=task.status, name=instance.name, instance_id=instance.id
            )
        )

    if data["status"] in {SUCCESS, FAILED}:
        delete_windows_resources.delay(instance.id)
        task.status = data["status"]
        LOGGER.info(
            "Secondary Volume Migration for Windows is '{status}' for instance '{name}' and ID:'{instance_id}' ".format(
                status=task.status, name=instance.name, instance_id=instance.id
            )
        )

    task.report = data
    doosradb.session.commit()

    return Response(status=204)
