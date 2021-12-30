import logging

from celery import chain

from doosra import db as doosradb
from doosra.common.consts import SUCCESS, IN_PROGRESS

from doosra.ibm.common.consts import PROVISIONING
from doosra.common.utils import DELETING, DELETED, CREATING, CREATION_PENDING, ERROR_CREATING, CREATED
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.models import (
    IBMLoadBalancer,
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("load_balancer_tasks.py")


@celery.task(name="initiate_load_balancer_provisioning")
def trigger_load_balancer_provisioning():
    ibm_load_balancers = doosradb.session.query(IBMLoadBalancer).filter_by(status=CREATION_PENDING).all()
    if not ibm_load_balancers:
        return

    for lb in ibm_load_balancers:
        instances, instance_count, task_id = list(), False, lb.base_task_id
        for pool in lb.pools.all():
            for pool_mem in pool.pool_members.all():
                if pool_mem.instance and pool_mem.instance not in instances:
                    instances.append(pool_mem.instance)

        if instances:
            instance_count = len(instances)

        for instance in instances:
            if instance.status in [CREATION_PENDING, CREATING]:
                break

            elif instance.status == ERROR_CREATING:
                lb.status = ERROR_CREATING

            elif instance.status == CREATED:
                for interface in instance.network_interfaces.all():
                    if interface.is_primary and not interface.private_ip:
                        break
                    instance_count -= 1

        if instance_count == 0:
            task_create_ibm_load_balancer.si(
                task_id=task_id, cloud_id=lb.cloud_id, region=lb.region, load_balancer_id=lb.id).delay()


@celery.task(name="create_ibm_load_balancer", base=IBMBaseTask, bind=True)
def task_create_ibm_load_balancer(self, task_id, cloud_id, region, load_balancer_id):
    """Create and configure load balancer"""

    ibm_load_balancer = doosradb.session.query(IBMLoadBalancer).filter_by(
        id=load_balancer_id, status=CREATION_PENDING).first()
    if not ibm_load_balancer:
        LOGGER.info("No IBMLoadBalancer found for ID: {}".format(load_balancer_id))
        return

    ibm_load_balancer.status = CREATING
    doosradb.session.commit()
    self.resource = ibm_load_balancer
    self.resource_type = "load_balancers"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )

    configured_lb = configure_and_save_obj_confs(self.ibm_manager, ibm_load_balancer)
    ibm_load_balancer.status = CREATED
    ibm_load_balancer.resource_id = configured_lb.resource_id
    ibm_load_balancer.provisioning_status = configured_lb.provisioning_status
    doosradb.session.commit()
    LOGGER.info(
        "IBM Load Balancer with name '{}' created successfully".format(ibm_load_balancer.name))
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_ibm_load_balancer", base=IBMBaseTask, bind=True)
def task_delete_ibm_load_balancer(self, task_id, cloud_id, region, load_balancer_id):
    """
    This request deletes a load balancer and its attached resources
    @return:
    """
    ibm_load_balancer = doosradb.session.query(IBMLoadBalancer).filter_by(id=load_balancer_id).first()
    if not ibm_load_balancer:
        return

    self.resource = ibm_load_balancer
    ibm_load_balancer.status = DELETING
    doosradb.session.commit()

    fetched_load_balancer = self.ibm_manager.rias_ops.fetch_ops.get_all_load_balancers(
        name=ibm_load_balancer.name, vpc_name=ibm_load_balancer.ibm_vpc_network.name,
        required_relations=False
    )

    if fetched_load_balancer:
        self.ibm_manager.rias_ops.delete_load_balancer(fetched_load_balancer[0])

    ibm_load_balancer.status = DELETED
    doosradb.session.delete(ibm_load_balancer)
    doosradb.session.commit()
    LOGGER.info("IBM Load Balancer '{name}' deleted successfully on IBM Cloud".format(name=ibm_load_balancer.name))


@celery.task(name="task_delete_ibm_load_balancer_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_load_balancer_workflow(self, task_id, cloud_id, region, load_balancer_id):
    """
    This request is workflow for the load balancer deletion
    @return:
    """

    workflow_steps = list()

    ibm_load_balancer = doosradb.session.query(IBMLoadBalancer).filter_by(id=load_balancer_id).first()
    if not ibm_load_balancer:
        return

    workflow_steps.append(task_delete_ibm_load_balancer.si(task_id=task_id, cloud_id=cloud_id,
                                                           region=region,
                                                           load_balancer_id=load_balancer_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
