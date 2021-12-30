import time

from doosra import db as doosradb
from doosra.common.consts import *
from doosra.gcp.clouds.consts import ERROR_REVOKE_ACCESS, ERROR_SYNC_CLOUD
from doosra.gcp.clouds.utils import revoke_cloud_access, sync_gcp_cloud_account
from doosra.gcp.common.utils import (
    get_regions,
    get_images,
    get_machine_types,
    get_zones,
)
from doosra.gcp.firewalls.utils import create_firewall_rule, delete_firewall_rule
from doosra.gcp.instance.utils import deploy_instance, delete_instance
from doosra.gcp.instance_groups.utils import (
    deploy_instance_group,
    delete_instance_group,
)
from doosra.gcp.load_balancers.utils import deploy_load_balancer, delete_load_balancer
from doosra.gcp.vpc.consts import ERROR_SYNC_REGIONS, ERROR_UPDATE_VPC
from doosra.gcp.vpc.utils import (
    deploy_vpc_network,
    delete_vpc_network,
    get_latest_vpc_networks,
    update_vpc_network,
)
from doosra.models.gcp_models import (
    GcpCloud,
    GcpCloudProject,
    GcpFirewallRule,
    GcpInstance,
    GcpInstanceGroup,
    GcpLoadBalancer,
    GcpTask,
    GcpVpcNetwork,
)
from doosra.tasks.celery_app import celery


@celery.task(name="delete_cloud_account", bind=True)
def task_revoke_cloud_access(self, cloud_id):
    time.sleep(1)
    status = True
    cloud_account = doosradb.session.query(GcpCloud).filter_by(id=cloud_id).first()
    if cloud_account and cloud_account.gcp_credentials:
        status = revoke_cloud_access(cloud_account.gcp_credentials.token)

    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task:
        if not status:
            task.status = FAILED
            task.message = ERROR_REVOKE_ACCESS
        else:
            task.status = SUCCESS
            doosradb.session.delete(cloud_account)
        doosradb.session.commit()


@celery.task(name="sync_clouds", bind=True)
def sync_cloud(self, cloud_id):
    """Sync Cloud Accounts"""
    time.sleep(1)
    status = sync_gcp_cloud_account(cloud_id)
    sync_task = (
        doosradb.session.query(GcpTask).filter_by(id=str(self.request.id)).first()
    )
    if sync_task and status:
        sync_task.status = SUCCESS
    elif sync_task:
        sync_task.status = FAILED
        sync_task.message = ERROR_SYNC_CLOUD
    doosradb.session.commit()


@celery.task(name="get_regions", bind=True)
def task_get_regions(self, cloud_project_id):
    time.sleep(1)
    regions = get_regions(cloud_project_id)
    sync_task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if sync_task and regions:
        sync_task.status = SUCCESS
        sync_task.result = {"regions": regions}
    elif sync_task:
        sync_task.message = ERROR_SYNC_REGIONS
        sync_task.status = FAILED
    doosradb.session.commit()


@celery.task(name="get_vpc_networks", bind=True)
def task_sync_vpc_networks(self, cloud_project_id):
    time.sleep(1)
    vpc_networks = get_latest_vpc_networks(cloud_project_id)
    sync_task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if sync_task and vpc_networks:
        sync_task.status = SUCCESS
        sync_task.result = {"vpc_networks": vpc_networks}
    elif sync_task:
        sync_task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_vpc_network", bind=True)
def task_create_vpc_network(self, cloud_project_id, vpc, description, subnets):
    time.sleep(1)
    cloud_project = (
        doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    )
    vpc, message = deploy_vpc_network(cloud_project, vpc, description, subnets)
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and vpc:
        task.status = SUCCESS
        task.resource_id = vpc.id
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="delete_vpc_network", bind=True)
def task_delete_vpc_network(self, vpc_id):
    time.sleep(1)
    vpc = GcpVpcNetwork.query.get(vpc_id)
    status, message = delete_vpc_network(vpc)
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="update_vpc_network", bind=True)
def task_update_vpc_network(self, vpc_id, subnets=None):
    time.sleep(1)
    vpc = GcpVpcNetwork.query.get(vpc_id)
    status = update_vpc_network(vpc, subnets)
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
        task.message = ERROR_UPDATE_VPC
    doosradb.session.commit()


@celery.task(name="get_zones", bind=True)
def task_get_zones(self, cloud_project_id):
    time.sleep(1)
    zones = get_zones(cloud_project_id)
    sync_task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if sync_task and zones:
        sync_task.status = SUCCESS
        sync_task.result = {"zones": zones}
    elif sync_task:
        sync_task.status = FAILED
    doosradb.session.commit()


@celery.task(name="get_images", bind=True)
def task_get_images(self, cloud_project_id):
    time.sleep(1)
    images = get_images(cloud_project_id)
    sync_task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if sync_task and images:
        sync_task.status = SUCCESS
        sync_task.result = {"images": images}
    elif sync_task:
        sync_task.status = FAILED
    doosradb.session.commit()


@celery.task(name="get_machine_types", bind=True)
def task_get_machine_type(self, cloud_project_id):
    time.sleep(1)
    mtypes = get_machine_types(cloud_project_id)
    sync_task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if sync_task and mtypes:
        sync_task.status = SUCCESS
        sync_task.result = {"machine_types": mtypes}
    elif sync_task:
        sync_task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_instance", bind=True)
def task_create_instance(
    self,
    cloud_project_id,
    zone,
    name,
    machine_type,
    description,
    network_tags,
    interfaces,
    disks,
):
    time.sleep(1)
    cloud_project = (
        doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    )
    instance, message = deploy_instance(
        cloud_project,
        zone,
        name,
        machine_type,
        interfaces,
        disks,
        network_tags,
        description,
    )
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task:
        if not instance:
            task.status = FAILED
            task.message = message
        else:
            task.status = SUCCESS
            task.resource_id = instance.id
        doosradb.session.commit()


@celery.task(name="delete_instance", bind=True)
def task_delete_instance(self, instance_id):
    time.sleep(1)
    instance = GcpInstance.query.get(instance_id)
    status, message = delete_instance(instance)
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="create_firewall_rule", bind=True)
def task_create_firewall_rule(self, vpc_id, firewall_name, data):
    time.sleep(1)
    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=vpc_id).first()
    firewall, message = create_firewall_rule(
        vpc,
        firewall_name,
        data.get("direction"),
        data.get("action"),
        tags=data.get("tags"),
        ip_ranges=data.get("ip_ranges"),
        priority=data.get("priority"),
        description=data.get("description"),
        target_tags=data.get("target_tags"),
        ip_protocols=data.get("ip_protocols"),
    )
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and firewall:
        task.status = SUCCESS
        task.resource_id = firewall.id
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="delete_firewall_rule", bind=True)
def task_delete_firewall_rule(self, firewall_id):
    time.sleep(1)
    firewall_rule = GcpFirewallRule.query.get(firewall_id)
    status, message = delete_firewall_rule(firewall_rule)
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="create_instance_group", bind=True)
def task_create_instance_group(self, cloud_project_id, instance_group_name, data):
    time.sleep(1)
    cloud_project = (
        doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    )
    instance_group, message = deploy_instance_group(
        cloud_project, instance_group_name, data
    )
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and instance_group:
        task.status = SUCCESS
        task.resource_id = instance_group.id
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="delete_instance_group", bind=True)
def task_delete_instance_group(self, instance_group_id):
    time.sleep(1)
    instance_group = GcpInstanceGroup.query.get(instance_group_id)
    status, message = delete_instance_group(instance_group)
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="create_load_balancer", bind=True)
def task_create_load_balancer(self, cloud_project_id, load_balancer_name, data):
    time.sleep(1)
    cloud_project = (
        doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    )
    load_balancer, message = deploy_load_balancer(
        cloud_project, load_balancer_name, data
    )
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and load_balancer:
        task.status = SUCCESS
        task.resource_id = load_balancer.id
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()


@celery.task(name="delete_load_balancer", bind=True)
def task_delete_load_balancer(self, load_balancer_id):
    time.sleep(1)
    load_balancer = GcpLoadBalancer.query.get(load_balancer_id)
    status, message = delete_load_balancer(load_balancer)
    task = (
        doosradb.session.query(GcpTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
        task.message = message
    doosradb.session.commit()
