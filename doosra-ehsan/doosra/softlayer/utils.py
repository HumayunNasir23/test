from flask import current_app

from doosra import db as doosradb
from doosra.migration.managers.exceptions import SLAuthError, SLExecuteError, SLInvalidRequestError, \
    SLRateLimitExceededError
from doosra.migration.managers.softlayer_manager import SoftLayerManager
from doosra.models import SoftlayerCloud


def validate_softlayer_account(softlayer_cloud_account):
    try:
        sl_manager = SoftLayerManager(
            username=softlayer_cloud_account.username, api_key=softlayer_cloud_account.api_key)
        sl_manager.fetch_ops.authenticate_sl_account()
        return True

    except (SLAuthError, SLExecuteError, SLInvalidRequestError, SLRateLimitExceededError) as ex:
        current_app.logger.info(ex)


def list_softlayer_instance_hostnames(project_id):
    """
    Get All Softlayer Clound Account instances Associated with a SofLayer cloud
    :return:
    """
    softlayer_cloud_accounts_list = list()
    softlayer_cloud_accounts = doosradb.session.query(SoftlayerCloud).filter_by(
        project_id=project_id, status='VALID').all()
    try:
        for softlayer_cloud_account in softlayer_cloud_accounts:
            softlayer_manager = SoftLayerManager(softlayer_cloud_account.username, softlayer_cloud_account.api_key)
            softlayer_cloud_accounts_list.append({
                "id": softlayer_cloud_account.id,
                "name": softlayer_cloud_account.name,
                "instances": softlayer_manager.fetch_ops.list_vsi_hostnames()
            })
    except (SLAuthError, SLExecuteError, SLInvalidRequestError, SLRateLimitExceededError) as ex:
        current_app.logger.info(ex)

    return {"classical_accounts": softlayer_cloud_accounts_list}


def get_classical_instance_details(project_id, instance_id):
    sl_cloud = doosradb.session.query(SoftlayerCloud).filter_by(project_id=project_id, status='VALID').first()
    sl_manager = SoftLayerManager(sl_cloud.username, sl_cloud.api_key)
    try:
        instance = sl_manager.fetch_ops.get_instance_details(instance_id=instance_id).to_ibm().to_json()
    except (SLAuthError, SLExecuteError, SLInvalidRequestError, SLRateLimitExceededError) as ex:
        current_app.logger.info(ex)
        return {"classical_instance": []}
    else:
        return {"classical_instance": instance}


def get_all_softlayer_cloud_accounts_images(project_id):
    """
    Get All Softlayer Clound Account images Associated with a SofLayer cloud
    :return:
    """
    softlayer_cloud_accounts_list = list()
    softlayer_cloud_accounts = doosradb.session.query(SoftlayerCloud).filter_by(
        project_id=project_id, status='VALID').all()
    try:
        for softlayer_cloud_account in softlayer_cloud_accounts:
            softlayer_manager = SoftLayerManager(softlayer_cloud_account.username, softlayer_cloud_account.api_key)
            softlayer_cloud_accounts_list.append({
                "id": softlayer_cloud_account.id,
                "name": softlayer_cloud_account.name,
                "images": softlayer_manager.fetch_ops.list_private_images_name()
            })
    except (SLAuthError, SLExecuteError, SLInvalidRequestError, SLRateLimitExceededError) as ex:
        current_app.logger.info(ex)
        return {"classical_accounts": []}

    return {"classical_accounts": softlayer_cloud_accounts_list}
