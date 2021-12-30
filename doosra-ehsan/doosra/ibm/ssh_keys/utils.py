from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMSshKey, IBMCloud


def configure_ssh_key(data):
    """
    Configuring IBM ssh-key on IBM cloud
    :return:
    """
    ssh_key = None
    ibm_cloud = IBMCloud.query.get(data["cloud_id"])
    if not ibm_cloud:
        current_app.logger.debug("IBM cloud with ID {} not found".format(data["cloud_id"]))
        return

    current_app.logger.info("Deploying IBM ssh key '{name}' on IBM Cloud".format(name=data["name"]))
    try:
        ibm_manager = IBMManager(ibm_cloud, data['region'])
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])
        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))
        existing_resource_group = existing_resource_group[0].get_existing_from_db() or existing_resource_group[0]

        existing_ssh_key_name = ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(name=data["name"])
        if existing_ssh_key_name:
            raise IBMInvalidRequestError("IBM ssh key with name '{}' already configured".format(data["name"]))

        existing_ssh_key = ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(public_key=data["public_key"])
        if existing_ssh_key:
            raise IBMInvalidRequestError("IBM ssh key with public key '{}' already configured".format(data["name"]))

        ssh_key = IBMSshKey(data['name'], data.get('type'), data['public_key'], data['region'])
        ssh_key.ibm_resource_group = existing_resource_group
        ssh_key.ibm_cloud = ibm_cloud
        doosradb.session.add(ssh_key)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_ssh_key(ssh_key)

        existing_ssh_key = ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(name=ssh_key.name)
        if existing_ssh_key:
            existing_ssh_key = existing_ssh_key[0]
            ssh_key.resource_id = existing_ssh_key.resource_id
            ssh_key.finger_print = existing_ssh_key.finger_print
            doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ssh_key.ibm_cloud.status = INVALID
        if ssh_key:
            ssh_key.status = ERROR_CREATING
        doosradb.session.commit()

    else:
        ssh_key.status = CREATED
        doosradb.session.commit()

    return ssh_key


def delete_ssh_key(ibm_ssh_key):
    """
    This request deletes a ssh key from IBM cloud
    :return:
    """
    current_app.logger.info("Deleting IBM ssh key '{name}' on IBM Cloud".format(name=ibm_ssh_key.name))
    try:
        ibm_manager = IBMManager(ibm_ssh_key.ibm_cloud, region=ibm_ssh_key.region)
        existing_ssh_key = ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(name=ibm_ssh_key.name)
        if existing_ssh_key:
            ibm_manager.rias_ops.delete_ssh_key(existing_ssh_key[0])
        ibm_ssh_key.status = DELETED
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_ssh_key.ibm_cloud.status = INVALID
        if ibm_ssh_key:
            ibm_ssh_key.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_ssh_key.status = DELETED
        doosradb.session.delete(ibm_ssh_key)
        doosradb.session.commit()
        return True

