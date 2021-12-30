import logging

from doosra import db as doosradb
from doosra.common.consts import IN_PROGRESS, SUCCESS, DELETED

from doosra.ibm.common.billing_utils import log_resource_billing
from doosra.ibm.common.consts import PROVISIONING
from doosra.common.utils import CREATED,CREATING, DELETING
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.models import IBMVpcRoute
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask

LOGGER = logging.getLogger("route_tasks.py")


@celery.task(name="configure_ibm_route", base=IBMBaseTask, bind=True)
def task_create_ibm_route(self, task_id, cloud_id, region, route_id):
    """Create IBMRoute and configures on ibm cloud"""
    ibm_route = doosradb.session.query(IBMVpcRoute).filter_by(id=route_id).first()
    if not ibm_route:
        return
    ibm_route.status = CREATING
    doosradb.session.commit()
    self.resource = ibm_route
    self.resource_type = "routes"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_route = configure_and_save_obj_confs(self.ibm_manager, ibm_route)
    ibm_route = configured_route.make_copy().add_update_db(ibm_route.ibm_vpc_network)
    ibm_route.status = CREATED
    doosradb.session.commit()
    LOGGER.info("IBM Route with name '{route}' created successfully".format(route=ibm_route.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_route)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="delete_ibm_route", base=IBMBaseTask, bind=True)
def task_delete_ibm_route(self, task_id, cloud_id, region, route_id):
    """
    This request deletes a VPC Route
    @return:
    """
    ibm_route = doosradb.session.query(IBMVpcRoute).filter_by(id=route_id).first()
    if not ibm_route:
        return

    self.resource = ibm_route
    ibm_route.status = DELETING
    doosradb.session.commit()

    fetched_routes = self.ibm_manager.rias_ops.fetch_ops.get_all_ibm_vpc_routes(
        name=ibm_route.name, vpc=ibm_route.ibm_vpc_network.name,
        required_relations=False
    )

    if fetched_routes:
        self.ibm_manager.rias_ops.delete_vpc_route(fetched_routes[0])

    ibm_route.status = DELETED
    doosradb.session.delete(ibm_route)
    doosradb.session.commit()
    LOGGER.info("IBM route '{name}' deleted successfully on IBM Cloud".format(name=ibm_route.name))
