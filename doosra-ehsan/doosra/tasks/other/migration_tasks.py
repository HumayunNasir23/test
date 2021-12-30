import json
import requests
import logging

from SoftLayer import VSManager, create_client_from_env

from doosra import db as doosradb
from doosra.common.consts import FAILED, SUCCESS, VALID
from doosra.common.utils import decrypt_api_key
from doosra.migration.models import CMModels
from doosra.migration.utils import migrate_vpc_configs
from doosra.models import MigrationTask, User
from doosra.tasks.celery_app import celery


LOGGER = logging.getLogger(__name__)


@celery.task(name="migrate_config_file")
def task_migrate_vpc(task_id, configs=None, user_name=None, api_key=None):
    ported_schema = migrate_vpc_configs(configs, user_name, api_key)
    task = doosradb.session.query(MigrationTask).filter_by(id=task_id).first()
    if not task:
        return

    if ported_schema:
        task.result = json.dumps({"vpcs": [ported_schema]})
        task.status = SUCCESS
    else:
        task.status = FAILED

    doosradb.session.commit()


@celery.task(name="add_content_migration_meta_data", bind=True)
def task_add_content_migration_meta_data(self, user_id, data):
    user = User.query.get(user_id)
    softlayer_clouds = user.project.softlayer_clouds.filter_by(status=VALID).all()
    for cloud in softlayer_clouds:
        client = create_client_from_env(cloud.username, decrypt_api_key(cloud.api_key))
        vs_manger = VSManager(client)
        try:
            vsi_id = vs_manger.list_instances(public_ip=data["ip"])[0]["id"]
            break
        except (KeyError, IndexError):
            vsi_id = None
    if not vsi_id:
        LOGGER.info(f"VSI Not Found for public IP: {data['ip']} against user: {user_id}")
        return
    cm_object = CMModels.query.filter_by(softlayer_vsi_id=vsi_id).first()
    if cm_object:
        cm_object.cm_meta_data = data
    else:
        cm_object = CMModels(softlayer_vsi_id=vsi_id, cm_meta_data=data)
        doosradb.session.add(cm_object)
    doosradb.session.commit()

    cm_object = CMModels.query.filter_by(softlayer_vsi_id=vsi_id).first()
    if cm_object:
        cm_object.cm_meta_data = data
    else:
        cm_object = CMModels(softlayer_vsi_id=vsi_id, cm_meta_data=data)
        doosradb.session.add(cm_object)
    doosradb.session.commit()
    LOGGER.info(f"VSI: {vsi_id} meta data saved for user: {user_id}")


@celery.task(name="start_nas_migration", bind=True)
def task_start_nas_migration(self, data, db_migration_api_key, db_migration_controller_host, user_id):

    get_all_locations_url = f"{db_migration_controller_host}/v1/dbmigration/locations?user_id={user_id}&limit=1000&start=1"

    headers = {'s-api-key': db_migration_api_key}
    response = requests.get(get_all_locations_url, headers=headers)
    if response.status_code != 200:
        LOGGER.info(
            f"NAS Migration Failed for user: {user_id} on getting locations with response {response.status_code}")
        return
    locations = data["locations"]
    src_migrator = data["src_migrator"]
    trg_migrator = data["trg_migrator"]
    src_migrator_id, trg_migrator_id = None, None
    for item in response.json()["items"]:
        if item["name"] == src_migrator:
            src_migrator_id = item["id"]
        elif item["name"] == trg_migrator:
            trg_migrator_id = item["id"]

        if src_migrator_id and trg_migrator_id:
            break
    if not (src_migrator_id and trg_migrator_id):
        LOGGER.info(f"NAS Migration Failed for user: {user_id} as src_migrator_id: {src_migrator_id} and "
                    f"trg_migrator_id: {trg_migrator_id}")
        return
    payload = {
        "name": "NAS-Migration",
        "databases": locations,
        "user_id": user_id,
        "src_location_id": src_migrator_id,
        "trg_location_id": trg_migrator_id
    }

    migration_post_url = db_migration_controller_host + "/v1/dbmigration/migrations"

    post_response = requests.post(url=migration_post_url, headers=headers, json=payload)
    if post_response.status_code not in [200, 201]:
        LOGGER.info(f"Content Migration Object Creation Payload: {payload}")
        LOGGER.info(f"NAS Migration Failed for user: {user_id} on creating migration object with status code "
                    f"{post_response.status_code}")
        return

    patch_response = requests.patch(
        url=f"{db_migration_controller_host}/v1/dbmigration/dbmigration/{post_response.json()['id']}", headers=headers)

    if post_response.status_code == 202:
        LOGGER.info(f"NAS Migration for user: {user_id} started with ID: {post_response.json()['id']}")
    else:
        LOGGER.info(f"NAS Migration for user: {user_id} started with status code: {patch_response.status_code}")
