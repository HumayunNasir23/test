import logging

from celery import chain, chord, group

from doosra import db as doosradb
from doosra.common.consts import IN_PROGRESS, SUCCESS

from doosra.ibm.common.billing_utils import log_resource_billing, IBMResourceGroup
from doosra.ibm.common.consts import PROVISIONING
from doosra.common.utils import  CREATING, CREATED, DELETING, DELETED, UPDATING
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.models import (
    IBMSubnet, IBMPublicGateway,)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_group_tasks, update_ibm_task
from doosra.tasks.ibm.floating_ip_tasks import task_delete_ibm_floating_ip
from doosra.tasks.ibm.instance_tasks import task_delete_ibm_instance
from doosra.tasks.ibm.load_balancer_tasks import task_delete_ibm_load_balancer
from doosra.tasks.ibm.vpn_tasks import task_delete_ibm_vpn_gateway

LOGGER = logging.getLogger("subnet_tasks.py")


@celery.task(name="configure_ibm_subnet", base=IBMBaseTask, bind=True)
def task_create_ibm_subnet(self, task_id, cloud_id, region, subnet_id, resource_group=None):
    """Create IBMSubnet and configures on ibm cloud"""
    ibm_subnet = doosradb.session.query(IBMSubnet).filter_by(id=subnet_id).first()
    if not ibm_subnet:
        return
    ibm_subnet.status = CREATING
    if resource_group:
        ibm_resource_group = IBMResourceGroup(name=resource_group, cloud_id=cloud_id)
        ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
        ibm_subnet.ibm_resource_group = ibm_resource_group

    doosradb.session.commit()
    self.resource = ibm_subnet
    self.resource_type = "subnets"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_subnet = configure_and_save_obj_confs(self.ibm_manager, ibm_subnet)
    ibm_subnet = configured_subnet.make_copy().add_update_db(ibm_subnet.ibm_vpc_network)
    LOGGER.info("IBM Subnet with name '{subnet}' created successfully".format(subnet=ibm_subnet.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_subnet)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_ibm_subnet", base=IBMBaseTask, bind=True)
def task_delete_ibm_subnet(self, task_id, cloud_id, region, subnet_id):
    """
    This request deletes a VPC Subnet
    @return:
    """
    ibm_subnet = doosradb.session.query(IBMSubnet).filter_by(id=subnet_id).first()
    if not ibm_subnet:
        return

    self.resource = ibm_subnet
    ibm_subnet.status = DELETING
    doosradb.session.commit()

    fetched_subnet = self.ibm_manager.rias_ops.fetch_ops.get_all_subnets(
        name=ibm_subnet.name, vpc=ibm_subnet.ibm_vpc_network.name,
        required_relations=False
    )

    if fetched_subnet:
        self.ibm_manager.rias_ops.delete_subnet(fetched_subnet[0])

    ibm_subnet.status = DELETED
    doosradb.session.delete(ibm_subnet)
    doosradb.session.commit()
    LOGGER.info("IBM subnet '{name}' deleted successfully on IBM Cloud".format(name=ibm_subnet.name))


@celery.task(name="task_delete_ibm_subnet_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_subnet_workflow(self, task_id, cloud_id, region, subnet_id):
    """
    This request deletes a VPC Subnet and its attached resources
    such as vpn gateways and its attached resources,load balancers
    and its attached resources,and the instances and its floating ip
    @return:
    """

    workflow_steps, subnet_tasks_list, floating_ip_tasks_list = list(), list(), list()
    vpn_instance_tasks_list, load_balancer_task_list = list(), list()
    ibm_subnet = doosradb.session.query(IBMSubnet).filter_by(id=subnet_id).first()
    if not ibm_subnet:
        return

    for lb in ibm_subnet.ibm_load_balancers:
        load_balancer_task_list.append(task_delete_ibm_load_balancer.si(
            task_id=task_id, cloud_id=cloud_id, region=region, load_balancer_id=lb.id))

    for vpn in ibm_subnet.vpn_gateways.all():
        vpn_instance_tasks_list.append(task_delete_ibm_vpn_gateway.si(
            task_id=task_id, cloud_id=cloud_id, region=region, vpn_id=vpn.id))

    for network_interface in ibm_subnet.network_interfaces.all():
        if network_interface.ibm_instance:
            if network_interface.floating_ip:
                floating_ip_tasks_list.append(
                    task_delete_ibm_floating_ip.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                                   floating_ip_id=network_interface.floating_ip.id))

        vpn_instance_tasks_list.append(task_delete_ibm_instance.si(
            task_id=task_id, cloud_id=cloud_id, region=region, instance_id=network_interface.ibm_instance.id))

    if load_balancer_task_list and len(load_balancer_task_list) == 1:
        workflow_steps.extend(load_balancer_task_list)
    elif load_balancer_task_list:
        workflow_steps.append(
            chord(group(load_balancer_task_list),
                  update_group_tasks.si(
                      task_id=task_id, cloud_id=cloud_id, region=region, message="Load Balancers Tasks Chord Finisher")))

    if floating_ip_tasks_list and len(floating_ip_tasks_list) == 1:
        workflow_steps.extend(floating_ip_tasks_list)
    elif floating_ip_tasks_list:
        workflow_steps.append(
            chord(group(floating_ip_tasks_list),
                  update_group_tasks.si(
                      task_id=task_id, cloud_id=cloud_id, region=region, message="Floating IP's Tasks Chord Finisher")))

    if vpn_instance_tasks_list and len(vpn_instance_tasks_list) == 1:
        workflow_steps.extend(vpn_instance_tasks_list)
    elif vpn_instance_tasks_list:
        workflow_steps.append(
            chord(group(vpn_instance_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="VPN/VSI's Tasks Chord Finisher")))

    workflow_steps.append(task_delete_ibm_subnet.si(
        task_id=task_id, cloud_id=cloud_id, region=region, subnet_id=ibm_subnet.id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_attach_public_gateway_to_subnet", base=IBMBaseTask, bind=True)
def task_attach_public_gateway_to_subnet(self, task_id, cloud_id, region, subnet_id, public_gateway_id):
    ibm_subnet = doosradb.session.query(IBMSubnet).filter_by(id=subnet_id).first()
    if not ibm_subnet:
        return

    ibm_subnet.status = UPDATING
    doosradb.session.commit()
    self.resource = ibm_subnet
    self.resource_type = "attach_pg_to_subnets"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS)

    ibm_public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(id=public_gateway_id).first()
    if not ibm_public_gateway:
        return

    self.ibm_manager.rias_ops.attach_public_gateway_to_subnet(ibm_subnet)
    ibm_subnet.status = CREATED
    doosradb.session.commit()
    LOGGER.info("IBM subnet '{name}' and IBM Public Gateway {pubgw} attached successfully on IBM Cloud".format(
        name=ibm_subnet.name, pubgw=ibm_public_gateway.name))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS)
