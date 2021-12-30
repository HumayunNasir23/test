import logging
import time

from doosra import db as doosradb
from doosra.common.consts import CREATED, FAILED, SUCCESS
from doosra.transit_gateway.common.consts import *
from doosra.transit_gateway.common.utils import list_transit_locations
from doosra.models import TransitGateway, TransitGatewayConnection, IBMCloud
from doosra.tasks import celery, IBMTask
from doosra.transit_gateway.utils import configure_transit_gateway, configure_transit_gateway_connection
from doosra.transit_gateway.utils import delete_transit_gateway, delete_transit_gateway_connection, \
    update_transit_gateway, update_transit_gateway_connection

LOGGER = logging.getLogger(__name__)


@celery.task(name="create_transit_gateway", bind=True)
def task_create_transit_gateway(self, name, cloud_id, data):
    transit_gateway = configure_transit_gateway(name, cloud_id, data)
    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=str(self.request.id).strip())
            .first()
    )
    if task and transit_gateway and transit_gateway.status == CREATED:
        task.status = SUCCESS
        task.resource_id = transit_gateway.id
    elif task and transit_gateway:
        task.status = FAILED
        task.resource_id = transit_gateway.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_transit_gateway_connection", bind=True)
def task_create_transit_gateway_connection(self, name, transit_gateway_id, cloud_id, data):
    transit_gateway_connection = configure_transit_gateway_connection(name, transit_gateway_id, cloud_id, data)
    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=str(self.request.id).strip())
            .first()
    )
    if (
            task
            and transit_gateway_connection
            and transit_gateway_connection.status == CREATED
    ):
        task.status = SUCCESS
        task.resource_id = transit_gateway_connection.id
    elif task and transit_gateway_connection:
        task.status = FAILED
        task.resource_id = transit_gateway_connection.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="task_update_transit_gateway", bind=True)
def task_update_transit_gateway(self, gateway_id):
    transit_gateway = TransitGateway.query.get(gateway_id)

    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=str(self.request.id).strip())
            .first()
    )
    if task and update_transit_gateway(transit_gateway):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="task_update_transit_gateway_connection", bind=True)
def task_update_transit_gateway_connection(self, connection_id):
    transit_gateway_connection = TransitGatewayConnection.query.get(connection_id)

    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=str(self.request.id).strip())
            .first()
    )
    if task and update_transit_gateway_connection(transit_gateway_connection):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_transit_gateway", bind=True)
def task_delete_transit_gateway(self, gateway_id):
    transit_gateway = TransitGateway.query.get(gateway_id)

    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=str(self.request.id).strip())
            .first()
    )
    if task and delete_transit_gateway(transit_gateway):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_transit_gateway_connection", bind=True)
def task_delete_transit_gateway_connection(self, connection_id):
    transit_gateway_connection = TransitGatewayConnection.query.get(connection_id)

    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=str(self.request.id).strip())
            .first()
    )
    if task and delete_transit_gateway_connection(transit_gateway_connection):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="list_transit_locations", bind=True)
def task_list_transit_locations(self, cloud_id):
    time.sleep(1)
    ibm_cloud = IBMCloud.query.get(cloud_id)
    locations = list_transit_locations(ibm_cloud)
    sync_task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if sync_task and locations:
        sync_task.status = SUCCESS
        sync_task.result = {"locations": locations}
    elif sync_task:
        sync_task.message = ERROR_SYNC_TRANSIT_LOCATION
        sync_task.status = FAILED
    doosradb.session.commit()
