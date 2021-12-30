from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMFloatingIP, IBMCloud


def configure_floating_ip(data):
    """
    Configuring IBM floating-ip on IBM cloud
    :return:
    """
    floating_ip = None
    ibm_cloud = IBMCloud.query.get(data["cloud_id"])
    if not ibm_cloud:
        current_app.logger.debug("IBM cloud with ID {} not found".format(data["cloud_id"]))
        return

    current_app.logger.info("Reserving IBM flaoting ip in zone '{name}' on IBM Cloud".format(name=data["zone"]))
    try:
        ibm_manager = IBMManager(ibm_cloud, data['region'])
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])
        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))
        existing_resource_group = existing_resource_group[0].get_existing_from_db() or existing_resource_group[0]

        floating_ip_name = ibm_manager.rias_ops.fetch_ops.get_available_floating_ip_name()
        floating_ip = IBMFloatingIP(floating_ip_name, data['region'], data['zone'])
        floating_ip.ibm_resource_group = existing_resource_group
        floating_ip.ibm_cloud = ibm_cloud

        doosradb.session.add(floating_ip)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_floating_ip(floating_ip)

        existing_floating_ip = ibm_manager.rias_ops.fetch_ops.get_all_floating_ips(name=floating_ip.name)
        if existing_floating_ip:
            existing_floating_ip = existing_floating_ip[0]
            floating_ip.resource_id = existing_floating_ip.resource_id
            floating_ip.finger_print = existing_floating_ip.finger_print
            doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            floating_ip.ibm_cloud.status = INVALID
        if floating_ip:
            floating_ip.status = ERROR_CREATING
        doosradb.session.commit()

    else:
        floating_ip.status = CREATED
        doosradb.session.commit()

    return floating_ip


def delete_floating_ip(ibm_floating_ip):
    """
    This request deletes a floating ip from IBM cloud
    :return:
    """
    current_app.logger.info("Deleting IBM floating ip '{name}' on IBM Cloud".format(name=ibm_floating_ip.name))
    try:
        ibm_manager = IBMManager(ibm_floating_ip.ibm_cloud, ibm_floating_ip.region)
        existing_floating_ip = ibm_manager.rias_ops.fetch_ops.get_all_floating_ips(name=ibm_floating_ip.name)
        if existing_floating_ip:
            ibm_manager.rias_ops.delete_floating_ip(existing_floating_ip[0])

        existing_floating_ip.status = DELETED
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_floating_ip.ibm_cloud.status = INVALID
        if ibm_floating_ip:
            ibm_floating_ip.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_floating_ip.status = DELETED
        doosradb.session.delete(ibm_floating_ip)
        doosradb.session.commit()
        return True

