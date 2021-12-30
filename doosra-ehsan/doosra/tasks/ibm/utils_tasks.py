import uuid

from doosra import db as doosradb
from doosra.common.consts import VALID
from doosra.common.utils import decrypt_api_key
from doosra.models import IBMCloud
from doosra.tasks.celery_app import celery


@celery.task(name="group_clouds_by_api_key")
def task_group_clouds_by_api_key():
    """
    Assign same group id to all clouds with same api-key
    """

    # TODO introduce pagination when clouds entries are mounting exorbitantly
    clouds = (
        doosradb.session.query(IBMCloud)
        .filter(
            IBMCloud.status.in_(
                [VALID]
            )
        )
        .all()
    )

    grouped_clouds_lib = {}
    clouds_lib = {}
    for cloud in clouds:
        if cloud.group_id:
            entry = grouped_clouds_lib.get(decrypt_api_key(cloud.api_key))
            if entry:
                grouped_clouds_lib[decrypt_api_key(cloud.api_key)].append(cloud)
            else:
                grouped_clouds_lib[decrypt_api_key(cloud.api_key)] = [cloud]

        else:
            entry = clouds_lib.get(decrypt_api_key(cloud.api_key))
            if entry:
                clouds_lib[decrypt_api_key(cloud.api_key)].append(cloud)
            else:
                clouds_lib[decrypt_api_key(cloud.api_key)] = [cloud]

    for key, clouds in clouds_lib.items():
        existing_group = grouped_clouds_lib.get(key)
        group_id = existing_group[0].group_id if existing_group else str(uuid.uuid4().hex)
        for cloud in clouds:
            cloud.group_id = group_id

    doosradb.session.commit()
