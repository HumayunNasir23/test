import json

from flask import current_app, jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.ibm.common.utils import construct_ibm_vpc_workspace_json
from doosra.ibm.vpcs import ibm_vpcs
from doosra.ibm.vpcs.schemas import *
from doosra.models import (
    IBMCloud,
    IBMNetworkAcl,
    IBMSubnet,
    IBMTask,
    IBMVpcNetwork,
    IBMVpcRoute,
    IBMAddressPrefix,
    WorkSpace,
)
from doosra.models import IBMInstanceTasks
from doosra.validate_json import validate_json
from .consts import *


@ibm_vpcs.route("/vpcs", methods=["POST"])
@validate_json(ibm_vpc_schema)
@authenticate
def add_ibm_vpc(user_id, user):
    """
    Add IBM VPC network
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """

    from doosra.tasks.ibm.vpcs_tasks import task_create_ibm_vpc_workflow

    data = request.get_json(force=True)
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(id=data["cloud_id"], project_id=user.project.id)
            .first()
    )
    if not cloud:
        current_app.logger.info(
            "No IBM cloud found with ID {id}".format(id=data["cloud_id"])
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not cloud.service_credentials:
        return Response("ERROR_COS_CREDENTIALS_MISSING", status=400)

    if data.get("kubernetes_clusters"):
        if not cloud.service_credentials.access_key_id and not cloud.service_credentials.secret_access_key:
            return Response("ERROR_HMAC_KEYS_MISSING", status=400)

    vpc = (
        doosradb.session.query(IBMVpcNetwork)
            .filter_by(name=data["name"], cloud_id=data["cloud_id"], region=data.get('region'))
            .first()
    )
    if vpc:
        return Response("ERROR_CONFLICTING_VPC_NAME", status=409)

    if data.get("subnets"):
        if len(data["subnets"]) > 15:
            return Response("ERROR_MAX_SUBNETS_LIMIT_REACHED", status=400)

    for instance in data.get("instances", []):
        if (instance.get("data_migration") or instance.get("image")["image_location"] in {
            IBMInstanceTasks.LOCATION_CLASSICAL_VSI,
            IBMInstanceTasks.LOCATION_CUSTOM_IMAGE,
            IBMInstanceTasks.LOCATION_COS_VHD,
            IBMInstanceTasks.LOCATION_COS_VMDK,
            IBMInstanceTasks.LOCATION_COS_QCOW2}) \
                and not cloud.service_credentials:
            return Response("ERROR_NO_SERVICE_CREDENTIALS", status=400)

    ibm_vpc_network = IBMVpcNetwork(
        name=data.get("name"),
        region=data.get("region"),
        classic_access=data.get("classic_access"),
        cloud_id=data.get("cloud_id"),
        address_prefix_management=data.get("address_prefix_management"),
    )

    doosradb.session.add(ibm_vpc_network)
    task = IBMTask(
        task_id=None, type_="VPC", region=data["region"], action="ADD", cloud_id=cloud.id,
        resource_id=ibm_vpc_network.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()
    workspace = None
    if data.get('is_workspace'):
        workspace = WorkSpace(
            name=ibm_vpc_network.name, type_="IBM", softlayer_id=data.get("softlayer_cloud_id"),
            project_id=user.project.id)
        workspace.ibm_vpc_network = ibm_vpc_network
        doosradb.session.add(workspace)
        doosradb.session.commit()

    task_create_ibm_vpc_workflow.delay(
        task_id=task.id, cloud_id=cloud.id, region=data["region"], data=data, vpc_id=ibm_vpc_network.id,
        softlayer_id=data.get("softlayer_cloud_id"))

    current_app.logger.info(VPC_CREATE.format(user.email))
    resp = jsonify({
        "task_id": task.id,
        "resource_id": ibm_vpc_network.id,
        "workspace_id": workspace.id if workspace else None
    })
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs", methods=["GET"])
@authenticate
def list_ibm_vpcs(user_id, user):
    """
    List all IBM VPC networks
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = (
        doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    )
    if not ibm_cloud_accounts:
        current_app.logger.info(
            "No IBM Cloud accounts found for project with ID {}".format(user.project.id)
        )
        return Response(status=204)

    vpc_networks_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        vpc_networks = ibm_cloud.vpc_networks.all()
        for vpc in vpc_networks:
            vpc_json = vpc.to_json()
            acls_json = list()
            for acl in vpc.acls.all():
                acl_json = acl.to_json()
                acl_json["subnets"] = [subnet.to_json() for subnet in acl.subnets.all()]
                acls_json.append(acl_json)

            vpc_json["acls"] = acls_json
            vpc_networks_list.append(vpc_json)

    if not vpc_networks_list:
        return Response(status=204)

    return jsonify(vpc_networks_list)


@ibm_vpcs.route("/report/<task_id>", methods=["GET"])
@authenticate
def get_ibm_vpc_task_report(user_id, user, task_id):
    """
    Get IBM Vpc network task
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    @param task_id:
    """
    task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not task:
        current_app.logger.info("No Task found with ID {task_id}".format(task_id=task_id))
        return Response(status=404)

    if not task.report:
        if task.status == FAILED:
            return jsonify({"status": task.status,
                            "message": task.message})
        return Response(status=204)

    return jsonify(task.report)


@ibm_vpcs.route("/workspaces", methods=["GET"])
@authenticate
def list_ibm_workspaces(user_id, user):
    """
    List all IBM Workspaces
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    workspaces_list = list()
    workspaces = doosradb.session.query(WorkSpace).filter_by(project_id=user.project.id).all()

    for workspace in workspaces:
        if workspace.ibm_vpc_network:
            if workspace.ibm_vpc_network.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
                continue

            workspaces_list.append(workspace.to_json())

    if not workspaces_list:
        return Response(status=204)

    return jsonify(workspaces_list)


@ibm_vpcs.route("/update/workspace/<workspace_id>", methods=["PATCH"])
@validate_json(ibm_vpc_schema)
@authenticate
def update_ibm_workspace(user_id, user, workspace_id):
    """
    Update IBM Workspace
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param workspace_id: vpc_id for VPC network
    :return: Response object from flask package
    """

    from doosra.tasks.ibm.vpcs_tasks import task_create_ibm_vpc_workflow

    data = request.get_json()
    workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
    if not workspace:
        current_app.logger.info("No Workspace found with ID {workspace_id}".format(workspace_id=workspace_id))
        return Response(status=404)

    if workspace.status == IN_PROGRESS:
        current_app.logger.info("Workspace with ID {workspace_id} Already UPDATING".format(workspace_id=workspace_id))
        return Response("Workspace Already Updating", status=405)

    workspace.status = IN_PROGRESS
    doosradb.session.commit()

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(
        id=workspace.ibm_vpc_network.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=workspace.ibm_vpc_network.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="VPC", region=data["region"], action="UPDATE", cloud_id=ibm_cloud.id,
        resource_id=workspace.ibm_vpc_network.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    task_create_ibm_vpc_workflow.delay(
        task_id=task.id, cloud_id=ibm_cloud.id, region=data["region"], data=data, vpc_id=workspace.ibm_vpc_network.id)
    current_app.logger.info(VPC_UPDATE.format(user.email))
    resp = jsonify({
        "task_id": task.id,
        "resource_id": workspace.ibm_vpc_network.id,
        "workspace_id": workspace.id
    })
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/workspace/<workspace_id>", methods=["GET"])
@authenticate
def get_ibm_workspace(user_id, user, workspace_id):
    """
    GET a Workspace by ID
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param workspace_id: workspace_id for Workspace
    :return: Response object from flask package
    """

    workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
    if not workspace:
        current_app.logger.info("No IBM WORKSPACE found with ID {id}".format(id=workspace_id))
        return Response(status=404)

    if not workspace.project_id == user.project.id:
        return Response("INVALID_WORKSPACE", status=400)

    if workspace.ibm_vpc_network and workspace.ibm_vpc_network.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    workspace_json = workspace.to_json()
    if workspace.ibm_vpc_network:
        workspace_json["vpc"] = construct_ibm_vpc_workspace_json(
            workspace.ibm_vpc_network.to_json(), workspace.request_metadata)

    return jsonify(workspace_json)


@ibm_vpcs.route("/create/workspace/<vpc_id>", methods=["PATCH"])
@authenticate
def create_ibm_workspace(user_id, user, vpc_id):
    """
    Create IBM Workspace
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: vpc_id for VPC network
    :return: Response object from flask package
    """

    ibm_vpc_network = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not ibm_vpc_network:
        current_app.logger.info("No IBM VPC found with ID {vpc_id}".format(vpc_id=vpc_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=ibm_vpc_network.cloud_id,
                                                           project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=ibm_vpc_network.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if ibm_vpc_network.workspace:
        current_app.logger.info(
            "Workspace already exists by name {vpc_name}".format(vpc_name=ibm_vpc_network.name))
        return Response(status=400)

    ibm_vpc_network.workspace = WorkSpace(name=ibm_vpc_network.name)
    ibm_vpc_network.workspace.project_id = user.project.id
    ibm_vpc_network.workspace.status = COMPLETED
    doosradb.session.commit()
    workspace_json = ibm_vpc_network.workspace.to_json()
    workspace_json["vpc"] = ibm_vpc_network.to_json()
    return jsonify(workspace_json)


@ibm_vpcs.route("/vpcs/<vpc_id>", methods=["GET"])
@authenticate
def get_ibm_vpc(user_id, user, vpc_id):
    """
    Get IBM Vpc network
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: vpc_id for VPC network
    :return: Response object from flask package
    """
    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No VPC found with ID {vpc_id}".format(vpc_id=vpc_id))
        return Response(status=404)

    ibm_cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(id=vpc.cloud_id, project_id=user.project.id)
            .first()
    )
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(
                cloud_id=vpc.cloud_id
            )
        )
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    vpc_json = vpc.to_json()
    acls_json = list()
    for acl in vpc.acls.all():
        acl_json = acl.to_json()
        acl_json["subnets"] = [subnet.to_json() for subnet in acl.subnets.all()]
        acls_json.append(acl_json)
    vpc_json["acls"] = acls_json

    return jsonify(vpc_json)


@ibm_vpcs.route("/vpcs/<vpc_id>", methods=["DELETE"])
@authenticate
def delete_ibm_vpc(user_id, user, vpc_id):
    """
    Delete an IBM VPC network
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: vpc_id for VPC network
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.vpcs_tasks import task_delete_ibm_vpc_workflow

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No IBM VPC found with ID {id}".format(id=vpc_id))
        return Response(status=404)

    if not vpc.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if vpc.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="VPC", region=vpc.region, action="DELETE", cloud_id=vpc.cloud_id,
        resource_id=vpc.id)

    doosradb.session.add(task)
    vpc.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_vpc_workflow.delay(task_id=task.id, cloud_id=vpc.cloud_id, region=vpc.region, vpc_id=vpc.id)

    current_app.logger.info(VPC_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/workspaces/<workspace_id>", methods=["DELETE"])
@authenticate
def delete_ibm_workspace(user_id, user, workspace_id):
    """
    Delete a Workspace
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param workspace_id: workspace_id for Workspace
    :return: Response object from flask package
    """

    workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
    if not workspace:
        current_app.logger.info("No IBM WORKSPACE found with ID {id}".format(id=workspace_id))
        return Response(status=404)

    if not workspace.project_id == user.project.id:
        return Response("INVALID_WORKSPACE", status=400)

    if workspace.ibm_vpc_network and workspace.ibm_vpc_network.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    doosradb.session.delete(workspace)
    doosradb.session.commit()
    return Response(status=202)


@ibm_vpcs.route("/vpcs/subnets", methods=["GET"])
@authenticate
def list_ibm_subnets(user_id, user):
    """
    List all IBM Subnets
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = (
        doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    )
    if not ibm_cloud_accounts:
        current_app.logger.info(
            "No IBM Cloud accounts found for project with ID {}".format(user.project.id)
        )
        return Response(status=204)
    subnet_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        subnets = doosradb.session.query(IBMSubnet).filter_by(cloud_id=ibm_cloud.id).all()
        for subnet in subnets:
            subnet_list.append(subnet.to_json())

    if not subnet_list:
        return Response(status=204)

    return jsonify(subnet_list)


@ibm_vpcs.route("/vpcs/subnets/<subnet_id>", methods=["GET"])
@authenticate
def get_ibm_subnet(user_id, user, subnet_id):
    """
    Get IBM subnet network
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param subnet_id: subnet_id for VPC subnets
    :return: Response object from flask package
    """
    snet = doosradb.session.query(IBMSubnet).filter_by(id=subnet_id).first()
    if not snet:
        current_app.logger.info("No Subnet found with ID {subnet_id}".format(subnet_id=subnet_id))
        return Response(status=404)

    if snet.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return jsonify(snet.to_json())


@ibm_vpcs.route("/vpcs/<vpc_id>/subnets", methods=["POST"])
@validate_json(ibm_subnet_schema)
@authenticate
def add_ibm_subnet(user_id, user, vpc_id):
    """
    Add IBM subnet
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: VPC ID for this request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_subnet

    data = request.get_json(force=True)
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(id=data["cloud_id"], project_id=user.project.id)
            .first()
    )
    if not cloud:
        current_app.logger.info(
            "No IBM cloud found with ID {id}".format(id=data["cloud_id"])
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    subnet = (
        doosradb.session.query(IBMSubnet)
            .filter_by(name=data["name"], vpc_id=vpc_id, zone=data["zone"])
            .first()
    )
    if subnet:
        return Response("ERROR_CONFLICTING_SUBNET_NAME", status=409)

    task = IBMTask(
        task_create_ibm_subnet.delay(data.get("name"), vpc_id, data, user_id, user.project.id).id,
        "SUBNET",
        "ADD",
        cloud.id,
        request_payload=json.dumps(data),
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(SUBNET_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/<vpc_id>/subnets/<subnet_id>", methods=["DELETE"])
@authenticate
def delete_ibm_subnet(user_id, user, vpc_id, subnet_id):
    """
    Delete an IBM subnet
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: vpc_id for IBM subnet
    :param subnet_id: subnet_id for IBM subnet
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.subnet_tasks import task_delete_ibm_subnet_workflow

    subnet = (
        doosradb.session.query(IBMSubnet).filter_by(id=subnet_id, vpc_id=vpc_id).first()
    )
    if not subnet:
        current_app.logger.info("No IBM Subnet found with ID {id}".format(id=subnet_id))
        return Response(status=404)

    if not subnet.ibm_vpc_network.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if subnet.ibm_vpc_network.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="SUBNET", region=subnet.region, action="DELETE",
        cloud_id=subnet.ibm_vpc_network.ibm_cloud.id, resource_id=subnet.id)

    doosradb.session.add(task)
    subnet.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_subnet_workflow.delay(task_id=task.id, cloud_id=subnet.ibm_vpc_network.ibm_cloud.id,
                                          region=subnet.region, subnet_id=subnet.id)

    current_app.logger.info(SUBNET_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/<vpc_id>/subnets/<subnet_id>/public_gateways", methods=["PUT"])
@validate_json(ibm_attach_subnet_to_public_gateway_schema)
@authenticate
def attach_subnet_to_public_gateway(user_id, user, vpc_id, subnet_id):
    """
    Add IBM subnet to Public Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: VPC ID for this request
    :param subnet_id: Subnet ID for this request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_attach_subnet_to_public_gateway

    data = request.get_json(force=True)
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(id=data["cloud_id"], project_id=user.project.id)
            .first()
    )
    if not cloud:
        current_app.logger.info(
            "No IBM cloud found with ID {id}".format(id=data["cloud_id"])
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    subnet = (
        doosradb.session.query(IBMSubnet).filter_by(id=subnet_id, vpc_id=vpc_id).first()
    )
    if not subnet:
        current_app.logger.info("No IBM Subnet found with ID {id}".format(id=subnet_id))
        return Response(status=404)

    if subnet.ibm_public_gateway:
        current_app.logger.info(
            "Public Gateway already attached to subnet with ID {id}".format(
                id=subnet_id
            )
        )
        return Response(status=400)

    task = IBMTask(
        task_attach_subnet_to_public_gateway.delay(subnet_id).id,
        "SUBNET",
        "UPDATE",
        cloud.id,
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(ATTACH_SUBNET_TO_PUBLIC_GATEWAY.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/<vpc_id>/subnets/<subnet_id>/public_gateways", methods=["DELETE"])
@validate_json(ibm_attach_subnet_to_public_gateway_schema)
@authenticate
def detach_subnet_to_public_gateway(user_id, user, vpc_id, subnet_id):
    """
    Detach IBM subnet to Public Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: VPC ID for this request
    :param subnet_id: Subnet ID for this request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_detach_subnet_to_public_gateway

    data = request.get_json(force=True)
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(id=data["cloud_id"], project_id=user.project.id)
            .first()
    )
    if not cloud:
        current_app.logger.info(
            "No IBM cloud found with ID {id}".format(id=data["cloud_id"])
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    subnet = (
        doosradb.session.query(IBMSubnet).filter_by(id=subnet_id, vpc_id=vpc_id).first()
    )
    if not subnet:
        current_app.logger.info("No IBM Subnet found with ID {id}".format(id=subnet_id))
        return Response(status=404)

    if not subnet.ibm_public_gateway:
        current_app.logger.info(
            "No Public Gateway attached to subnet with ID {id}".format(id=subnet_id)
        )
        return Response(status=400)

    task = IBMTask(
        task_detach_subnet_to_public_gateway.delay(subnet_id).id,
        "SUBNET",
        "UPDATE",
        cloud.id,
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(DETACH_SUBNET_TO_PUBLIC_GATEWAY.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/<vpc_id>/subnets/<subnet_id>/acls", methods=["PUT"])
@validate_json(ibm_attach_subnet_to_public_gateway_schema)
@authenticate
def attach_subnet_to_acl(user_id, user, vpc_id, subnet_id):
    """
    Add IBM subnet to Network ACL
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: VPC ID for this request
    :param subnet_id: Subnet ID for this request
    :param acl_id: Network ACL ID for this request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_attach_subnet_to_acl

    data = request.get_json(force=True)
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(id=data["cloud_id"], project_id=user.project.id)
            .first()
    )
    if not cloud:
        current_app.logger.info(
            "No IBM cloud found with ID {id}".format(id=data["cloud_id"])
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    subnet = (
        doosradb.session.query(IBMSubnet).filter_by(id=subnet_id, vpc_id=vpc_id).first()
    )
    if not subnet:
        current_app.logger.info("No IBM Subnet found with ID {id}".format(id=subnet_id))
        return Response(status=404)

    acl = (
        doosradb.session.query(IBMNetworkAcl)
            .filter_by(id=data["acl_id"], cloud_id=data["cloud_id"])
            .first()
    )
    if not subnet:
        current_app.logger.info(
            "No IBM Network ACL found with ID {id}".format(id=data["acl_id"])
        )
        return Response(status=404)

    task = IBMTask(
        task_attach_subnet_to_acl.delay(subnet_id, acl.id).id,
        "SUBNET",
        "UPDATE",
        cloud.id,
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(ATTACH_SUBNET_TO_ACL.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/<vpc_id>/address_prefixes", methods=["POST"])
@validate_json(ibm_vpc_address_prefix)
@authenticate
def create_ibm_vpc_address_prefix(user_id, user, vpc_id):
    """
    Add an IBM vpc address prefix
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_vpc_address_prefix

    vpc = (
        doosradb.session.query(IBMVpcNetwork)
            .filter_by(id=vpc_id).first()
    )
    data = request.get_json(force=True)

    cloud = (
        doosradb.session.query(IBMCloud).filter_by(id=vpc.cloud_id, project_id=user.project.id).first()
    )
    if not cloud:
        current_app.logger.info(
            "No IBM cloud project found with ID {id}".format(id=vpc.cloud_id)
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_create_ibm_vpc_address_prefix.delay(data, vpc.id, user_id, user.project.id).id,
        "ADDRESS-PREFIX",
        "ADD",
        cloud.id,
        request_payload=json.dumps(data),
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(CREATE_ADDRESS_PREFIX.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/<vpc_id>/address_prefix/<address_prefix_id>", methods=["DELETE"])
@authenticate
def delete_ibm_vpc_address_prefix(user_id, user, vpc_id, address_prefix_id):
    """
    Delete an IBM vpc address prefix
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.address_prefix_tasks import task_delete_address_prefix_workflow

    address_prefix = (
        doosradb.session.query(IBMAddressPrefix).filter_by(id=address_prefix_id).first()
    )
    if not address_prefix:
        current_app.logger.info(
            "No IBM address prefix found with ID {id}".format(id=address_prefix_id)
        )
        return Response(status=404)

    if not address_prefix.ibm_vpc_network.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if address_prefix.ibm_vpc_network.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="ADDRESS-PREFIX", region=address_prefix.ibm_vpc_network.region, action="DELETE",
        cloud_id=address_prefix.ibm_vpc_network.cloud_id, resource_id=address_prefix.id)

    doosradb.session.add(task)
    doosradb.session.commit()

    task_delete_address_prefix_workflow.delay(task_id=task.id, cloud_id=address_prefix.ibm_vpc_network.cloud_id,
                                              region=address_prefix.ibm_vpc_network.region,
                                              addr_prefix_id=address_prefix.id)

    current_app.logger.info(DELETE_ADDRESS_PREFIX.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/address_prefix", methods=["GET"])
@authenticate
def list_ibm_vpc_address_prefixes(user_id, user):
    """
    Get IBM address prefixes
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    address_prefix_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        for vpc in ibm_cloud.vpc_networks.all():
            for address_prefix in vpc.address_prefixes.all():
                address_prefix_list.append(address_prefix.to_json())

    if not address_prefix_list:
        return Response(status=204)

    return Response(json.dumps(address_prefix_list), mimetype='application/json')


@ibm_vpcs.route("/vpcs/<vpc_id>/address_prefix", methods=["GET"])
@authenticate
def get_ibm_vpc_address_prefixes(user_id, user, vpc_id):
    """
    Get IBM address prefixes
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud = (
        doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).first()
    )
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {user_id}".format(
                user_id=user.project.id
            )
        )
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    ibm_vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not ibm_vpc:
        current_app.logger.info("No IBM VPC found with ID {id}".format(id=vpc_id))
        return Response(status=404)

    address_prefixes = ibm_vpc.address_prefixes.all()

    address_prefix_list = list()
    for address_prefix in address_prefixes:
        address_prefix_list.append(address_prefix.to_json())

    return Response(json.dumps(address_prefix_list), mimetype="application/json")


@ibm_vpcs.route("/vpcs/address_prefix/<address_prefix_id>", methods=["GET"])
@authenticate
def get_ibm_vpc_address_prefix(user_id, user, address_prefix_id):
    """
    Get IBM address prefixes
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud = (
        doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).first()
    )
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {user_id}".format(
                user_id=user.project.id
            )
        )
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    address_prefix = (
        doosradb.session.query(IBMAddressPrefix).filter_by(id=address_prefix_id).first()
    )
    if not address_prefix:
        current_app.logger.info(
            "No IBM address prefix found with ID {id}".format(id=address_prefix_id)
        )
        return Response(status=404)

    return Response(json.dumps(address_prefix.to_json()), mimetype="application/json")


@ibm_vpcs.route("/vpcs/<vpc_id>/routes", methods=["POST"])
@validate_json(ibm_routes_schema)
@authenticate
def add_ibm_vpc_route(user_id, user, vpc_id):
    """
        Add Route to IBM VPC network
        :param vpc_id: ID of the VPC
        :param user_id: ID of the user initiating the request
        :param user: object of the user initiating the request
        :return: Response object from flask package
        """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_route_for_vpc_network

    data = request.get_json(force=True)

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        "No IBM cloud found with ID {id}".format(id=data["vpc_id"])
        return Response(status=404)

    cloud = doosradb.session.query(IBMCloud).filter_by(id=vpc.cloud_id, project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info(
            "No IBM cloud found with ID {id}".format(id=vpc.cloud_id)
        )
        return Response(status=400)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    vpc_route = doosradb.session.query(IBMVpcRoute).filter_by(name=data["name"], cloud_id=cloud.id,
                                                              region=data.get('region')).first()
    if vpc_route:
        return Response("ERROR_CONFLICTING_VPC_ROUTE_NAME", status=409)

    vpc_route = doosradb.session.query(IBMVpcRoute).filter_by(cloud_id=cloud.id,
                                                              next_hop_address=data["next_hop_address"],
                                                              destination=data["destination"]).first()

    if vpc_route and not (
            vpc_route.next_hop_address == data["next_hop_address"]
            and vpc_route.destination == data["destination"]
    ):
        return Response(
            "ERROR: CHANGE ONE OF THESE(ALREADY EXISTS)\nNEXT_HOP_ADDRESS {next_hop_address}\nDESTINATION {destination}".format(
                next_hop_address=data["next_hop_address"],
                destination=data["destination"],
            ),
            status=400,
        )

    task = IBMTask(
        task_create_ibm_route_for_vpc_network.delay(cloud.id, vpc_id, data, user_id, user.project.id).id,
        "VPC-ROUTE",
        "ADD",
        cloud.id,
        region=vpc.region,
        request_payload=json.dumps(data),
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(VPC_ROUTE_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpcs.route("/vpcs/<vpc_id>/routes", methods=["GET"])
@authenticate
def list_ibm_vpc_routes(user_id, user, vpc_id):
    """ List all IBM Routes for a VPC
    :param vpc_id: VPC ID
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = (
        doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    )
    if not ibm_cloud_accounts:
        current_app.logger.info(
            "No IBM Cloud accounts found for project with ID {}".format(user.project.id)
        )
        return Response(status=204)

    vpc_routes_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        vpc_routes = ibm_cloud.vpc_routes.all()
        for route in vpc_routes:
            vpc_routes_list.append(route.to_json())

    if not vpc_routes_list:
        return Response(status=204)

    return jsonify(vpc_routes_list)


@ibm_vpcs.route("/vpcs/routes/<route_id>", methods=["GET"])
@authenticate
def get_ibm_vpc_routes(user_id, user, route_id):
    """
    Get IBM routes
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud = (
        doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).first()
    )
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {user_id}".format(
                user_id=user.project.id
            )
        )
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    route = (
        doosradb.session.query(IBMVpcRoute).filter_by(id=route_id).first()
    )
    if not route:
        current_app.logger.info(
            "No IBM Route found with ID {id}".format(id=route_id)
        )
        return Response(status=404)

    return Response(json.dumps(route.to_json()), mimetype="application/json")


@ibm_vpcs.route("/vpcs/<vpc_id>/routes/<id>", methods=["DELETE"])
@authenticate
def delete_ibm_vpc_routes(user_id, user, vpc_id, id):
    """ This request deletes a route. This operation cannot be reversed.
    :param vpc_id: VPC ID
    :param user_id: ID of the user initiating the request
    :param id: ID of the Route to Delete
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.vpcs_tasks import task_delete_ibm_vpc_route_workflow

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    vpc_route = (
        doosradb.session.query(IBMVpcRoute).filter_by(id=id, vpc_id=vpc_id).first()
    )
    if not vpc:
        current_app.logger.info("No IBM VPC found with ID {id}".format(id=vpc_id))
        return Response(status=404)

    if not vpc_route:
        current_app.logger.info(
            "No IBM Route `{route_id}` found for the VPC with ID `{vpc_id}`".format(
                route_id=id, vpc_id=vpc_id
            )
        )

    if not vpc.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if vpc.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="VPC-ROUTE", region=vpc.region, action="DELETE",
        cloud_id=vpc.cloud_id, resource_id=vpc_route.id)

    doosradb.session.add(task)
    vpc_route.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_vpc_route_workflow.delay(task_id=task.id, cloud_id=vpc.cloud_id,
                                             region=vpc.region, vpc_route_id=vpc_route.id)

    current_app.logger.info(VPC_ROUTE_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
