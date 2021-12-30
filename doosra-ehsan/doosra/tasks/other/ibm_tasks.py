import time

from doosra import db as doosradb
from doosra.common.consts import CREATED, FAILED, SUCCESS
from doosra.ibm.acls.utils import (
    configure_network_acl,
    configure_network_acl_rule,
    delete_network_acl, delete_network_acl_rule)
from doosra.ibm.clouds.utils import verify_cloud_credentials
from doosra.ibm.common.billing_utils import log_resource_billing
from doosra.ibm.common.consts import *
from doosra.ibm.common.utils import (
    get_ibm_address_prefixes,
    get_ibm_regions,
    get_ibm_resource_groups,
    get_ibm_zones,
    get_ibm_images,
    get_ibm_operating_systems,
    get_ibm_instance_profiles,
    get_ibm_volume_profiles,
    get_cos_buckets,
)
from doosra.ibm.discovery.ibm_dc import IBMDiscoveryClient
from doosra.ibm.floating_ips.utils import delete_floating_ip
from doosra.ibm.floating_ips.utils import configure_floating_ip
from doosra.ibm.images.utils import configure_image, delete_image
from doosra.ibm.instances.utils import configure_ibm_instance, delete_ibm_instance
from doosra.ibm.load_balancers.utils import delete_load_balancer
from doosra.ibm.load_balancers.utils import (
    configure_load_balancer,
)
from doosra.ibm.public_gateways.utils import (
    configure_public_gateway,
    delete_public_gateway)
from doosra.ibm.security_groups.utils import (
    configure_ibm_security_group,
    configure_ibm_security_group_rule,
    delete_ibm_security_group_rule, delete_ibm_security_group)
from doosra.ibm.ssh_keys.utils import configure_ssh_key, delete_ssh_key
from doosra.ibm.vpcs.utils import (
    attach_network_acl,
    attach_public_gateway,
    detach_public_gateway,
    delete_ibm_vpc_route, delete_address_prefix, delete_ibm_subnet, delete_ibm_vpc)
from doosra.ibm.vpcs.utils import configure_address_prefix
from doosra.ibm.vpcs.utils import (
    configure_ibm_subnet,
    configure_ibm_vpc,
)
from doosra.ibm.vpcs.utils import configure_ibm_vpc_route
from doosra.ibm.vpns.utils import (
    configure_ibm_ipsec_policy,
    configure_ibm_ike_policy,
    configure_ibm_vpn_gateway,
    configure_ibm_vpn_connection,
    delete_ibm_vpn_connection, delete_ibm_vpn_gateway, delete_ibm_ipsec_policy, delete_ibm_ike_policy)
from doosra.models import (
    IBMCloud,
    IBMNetworkAcl,
    IBMNetworkAclRule,
    IBMSubnet,
    IBMTask,
    IBMVpcNetwork,
    IBMLoadBalancer,
    IBMInstance,
    IBMPublicGateway,
    IBMSecurityGroup,
    IBMSecurityGroupRule,
    IBMIKEPolicy,
    IBMIPSecPolicy,
    IBMVpnGateway,
    IBMVpnConnection,
    IBMSshKey,
    IBMFloatingIP,
    IBMAddressPrefix,
    IBMImage,
    IBMVpcRoute,
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.utils_tasks import task_group_clouds_by_api_key


@celery.task(name="process_new_ibm_cloud")
def task_process_new_ibm_cloud_account(cloud_id):
    cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id).first()
    if cloud:
        verify_cloud_credentials(cloud)

        # re group all clouds by api key when new cloud is added
        task_group_clouds_by_api_key.delay()


@celery.task(name="get_ibm_regions")
def task_get_regions(task_id, cloud_id):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    regions = get_ibm_regions(ibm_cloud)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if regions:
        sync_task.status = SUCCESS
        sync_task.result = {"regions": regions}
    else:
        sync_task.message = ERROR_SYNC_REGIONS
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="get_ibm_zones")
def task_get_zones(task_id, cloud_id, region):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    zones = get_ibm_zones(ibm_cloud, region)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if zones:
        sync_task.status = SUCCESS
        sync_task.result = {"zones": zones}
    else:
        sync_task.message = ERROR_SYNC_ZONES
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="get_ibm_resource_groups")
def task_get_resource_groups(task_id, cloud_id):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    resource_groups = get_ibm_resource_groups(ibm_cloud)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if resource_groups:
        sync_task.status = SUCCESS
        sync_task.result = {
            "resource_groups": [
                resource_group.name for resource_group in resource_groups
            ]
        }
    else:
        sync_task.message = ERROR_SYNC_RESOURCE_GROUPS
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="get_ibm_address_prefixes")
def task_get_ibm_address_prefixes(task_id, vpc_id):
    ibm_vpc = IBMVpcNetwork.query.get(vpc_id)
    address_prefixes = get_ibm_address_prefixes(ibm_vpc)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if address_prefixes:
        sync_task.status = SUCCESS
        sync_task.result = {"address_prefixes": address_prefixes}
    else:
        sync_task.message = ERROR_SYNC_ADDRESS_PREFIXES
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="create_ibm_vpc_network", bind=True)
def task_create_ibm_vpc_network(self, cloud_id, vpc_name, region, data, user_id, project_id):
    time.sleep(1)
    vpc = configure_ibm_vpc(cloud_id, vpc_name, region, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and vpc and vpc.status == CREATED:
        task.status = SUCCESS
        task.resource_id = vpc.id
        log_resource_billing(user_id, project_id, vpc)
    elif task and vpc:
        task.status = FAILED
        task.resource_id = vpc.id
    elif task:
        task.status = FAILED

    doosradb.session.commit()


@celery.task(name="delete_ibm_vpc_network", bind=True)
def task_delete_ibm_vpc_network(self, vpc_id):
    time.sleep(1)
    ibm_vpc = IBMVpcNetwork.query.get(vpc_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_vpc(ibm_vpc):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_subnet", bind=True)
def task_create_ibm_subnet(self, name, vpc_id, data, user_id, project_id):
    time.sleep(1)
    ibm_vpc = IBMVpcNetwork.query.get(vpc_id)
    subnet = configure_ibm_subnet(name, ibm_vpc, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and subnet and subnet.status == CREATED:
        task.status = SUCCESS
        task.resource_id = subnet.id
        log_resource_billing(user_id, project_id, subnet)
    elif task and subnet:
        task.status = FAILED
        task.resource_id = subnet.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_subnets", bind=True)
def task_delete_ibm_subnet(self, subnet_id):
    time.sleep(1)
    ibm_subnet = IBMSubnet.query.get(subnet_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_subnet(ibm_subnet):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_network_acl", bind=True)
def task_create_ibm_network_acl(self, cloud_id, acl_name, region, data, user_id, project_id):
    time.sleep(1)
    ibm_acl = configure_network_acl(cloud_id, acl_name, region, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_acl and ibm_acl.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_acl.id
        log_resource_billing(user_id, project_id, ibm_acl)
    elif task and ibm_acl:
        task.status = FAILED
        task.resource_id = ibm_acl.id
    elif task:
        task.status = FAILED

    doosradb.session.commit()


@celery.task(name="create_ibm_network_acl_rule", bind=True)
def task_create_ibm_network_acl_rule(self, rule_name, acl_id, data, user_id, project_id):
    time.sleep(1)
    ibm_acl_rule = configure_network_acl_rule(acl_id, rule_name, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_acl_rule and ibm_acl_rule.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_acl_rule.id
        log_resource_billing(user_id, project_id, ibm_acl_rule)
    elif task and ibm_acl_rule:
        task.status = FAILED
        task.resource_id = ibm_acl_rule.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_network_acls", bind=True)
def task_delete_ibm_network_acl(self, acl_id):
    time.sleep(1)
    ibm_network_acl = IBMNetworkAcl.query.get(acl_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_network_acl(ibm_network_acl):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_network_acl_rules", bind=True)
def task_delete_ibm_network_acl_rule(self, acl_rule_id):
    time.sleep(1)
    ibm_network_acl_rule = IBMNetworkAclRule.query.get(acl_rule_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_network_acl_rule(ibm_network_acl_rule):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_security_group", bind=True)
def task_create_ibm_security_group(self, name, vpc_id, data, user_id, project_id):
    time.sleep(1)
    ibm_security_group = configure_ibm_security_group(name, vpc_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_security_group and ibm_security_group.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_security_group.id
        log_resource_billing(user_id, project_id, ibm_security_group)
    elif task and ibm_security_group:
        task.status = FAILED
        task.resource_id = ibm_security_group.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_security_group", bind=True)
def task_delete_ibm_security_group(self, security_group_id):
    time.sleep(1)
    ibm_security_group = IBMSecurityGroup.query.get(security_group_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_security_group(ibm_security_group):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_security_group_rule", bind=True)
def task_create_ibm_security_group_rule(self, security_group_id, data, user_id, project_id):
    time.sleep(1)
    ibm_security_group_rule = configure_ibm_security_group_rule(security_group_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_security_group_rule and ibm_security_group_rule.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_security_group_rule.id
        log_resource_billing(user_id, project_id, ibm_security_group_rule)
    elif task and ibm_security_group_rule:
        task.status = FAILED
        task.resource_id = ibm_security_group_rule.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_security_group_rule", bind=True)
def task_delete_ibm_security_group_rule(self, security_group_rule_id):
    time.sleep(1)
    ibm_security_group_rule = IBMSecurityGroupRule.query.get(security_group_rule_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_security_group_rule(ibm_security_group_rule):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="configure_ibm_public_gateway", bind=True)
def task_create_ibm_public_gateway(self, name, vpc_id, data, user_id, project_id):
    time.sleep(1)
    ibm_public_gateway = configure_public_gateway(name, vpc_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_public_gateway and ibm_public_gateway.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_public_gateway.id
        log_resource_billing(user_id, project_id, ibm_public_gateway)
    elif task and ibm_public_gateway:
        task.status = FAILED
        task.resource_id = ibm_public_gateway.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_public_gateways", bind=True)
def task_delete_ibm_public_gateway(self, public_gateway_id):
    time.sleep(1)
    ibm_public_gateway = IBMPublicGateway.query.get(public_gateway_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_public_gateway(ibm_public_gateway):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="attach_subnet_to_public_gateway", bind=True)
def task_attach_subnet_to_public_gateway(self, subnet_id):
    time.sleep(1)
    ibm_subnet = IBMSubnet.query.get(subnet_id)
    status = attach_public_gateway(ibm_subnet)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="detach_subnet_to_public_gateway", bind=True)
def task_detach_subnet_to_public_gateway(self, subnet_id):
    time.sleep(1)
    ibm_subnet = IBMSubnet.query.get(subnet_id)
    status = detach_public_gateway(ibm_subnet)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="attach_subnet_to_acl", bind=True)
def task_attach_subnet_to_acl(self, subnet_id, acl_id):
    time.sleep(1)
    ibm_subnet = IBMSubnet.query.get(subnet_id)
    status = attach_network_acl(ibm_subnet, acl_id)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and status:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="configure_ibm_ike_policy", bind=True)
def task_create_ibm_ike_policy(self, name, cloud_id, data, user_id, project_id):
    time.sleep(1)
    ibm_ike_policy = configure_ibm_ike_policy(name, cloud_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_ike_policy and ibm_ike_policy.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_ike_policy.id
        log_resource_billing(user_id, project_id, ibm_ike_policy)
    elif task and ibm_ike_policy:
        task.status = FAILED
        task.resource_id = ibm_ike_policy.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_instance", bind=True)
def task_create_ibm_instance(self, name, vpc_id, data):
    time.sleep(1)
    ibm_instance = configure_ibm_instance(name, vpc_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_instance and ibm_instance.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_instance.id
    elif task and ibm_instance:
        task.status = FAILED
        task.resource_id = ibm_instance.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="configure_ibm_ipsec_policy", bind=True)
def task_create_ibm_ipsec_policy(self, name, cloud_id, data, user_id, project_id):
    time.sleep(1)
    ibm_ipsec_policy = configure_ibm_ipsec_policy(name, cloud_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_ipsec_policy and ibm_ipsec_policy.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_ipsec_policy.id
        log_resource_billing(user_id, project_id, ibm_ipsec_policy)
    elif task and ibm_ipsec_policy:
        task.status = FAILED
        task.resource_id = ibm_ipsec_policy.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_ike_policy", bind=True)
def task_delete_ibm_ike_policy(self, ike_policy_id):
    time.sleep(1)
    ibm_ike_policy = IBMIKEPolicy.query.get(ike_policy_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_ike_policy(ibm_ike_policy):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_instance", bind=True)
def task_delete_ibm_instance(self, instance_id):
    time.sleep(1)
    ibm_instance = IBMInstance.query.get(instance_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_instance(ibm_instance):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_ipsec_policy", bind=True)
def task_delete_ibm_ipsec_policy(self, ipsec_policy_id):
    time.sleep(1)
    ibm_ipsec_policy = IBMIPSecPolicy.query.get(ipsec_policy_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_ipsec_policy(ibm_ipsec_policy):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_vpn_gateway", bind=True)
def task_create_ibm_vpn_gateway(self, name, vpc_id, data, user_id, project_id):
    time.sleep(1)
    ibm_vpn_gateway = configure_ibm_vpn_gateway(name, vpc_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_vpn_gateway and ibm_vpn_gateway.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_vpn_gateway.id
        log_resource_billing(user_id, project_id, ibm_vpn_gateway)
    elif task and ibm_vpn_gateway:
        task.status = FAILED
        task.resource_id = ibm_vpn_gateway.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_vpn_gateway", bind=True)
def task_delete_ibm_vpn_gateway(self, vpn_gateway_id):
    time.sleep(1)
    ibm_vpn = IBMVpnGateway.query.get(vpn_gateway_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_vpn_gateway(ibm_vpn):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_vpn_gateway_connection", bind=True)
def task_create_ibm_vpn_connection(self, name, cloud_id, data, user_id, project_id):
    time.sleep(1)
    ibm_vpn_gateway_connection = configure_ibm_vpn_connection(name, cloud_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if (
        task
        and ibm_vpn_gateway_connection
        and ibm_vpn_gateway_connection.status == CREATED
    ):
        task.status = SUCCESS
        task.resource_id = ibm_vpn_gateway_connection.id
        log_resource_billing(user_id, project_id, ibm_vpn_gateway_connection)
    elif task and ibm_vpn_gateway_connection:
        task.status = FAILED
        task.resource_id = ibm_vpn_gateway_connection.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_vpn_connection", bind=True)
def task_delete_ibm_vpn_connection(self, vpn_gateway_id, vpn_connection_id):
    time.sleep(1)
    ibm_vpn_connection = IBMVpnConnection.query.get(vpn_connection_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_vpn_connection(ibm_vpn_connection):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="get_ibm_images")
def task_get_images(task_id, cloud_id, region):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    images = get_ibm_images(ibm_cloud, region)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if images:
        sync_task.status = SUCCESS
        images_dict = dict()
        for image in images:
            if not image.operating_system:
                continue
            if image.operating_system.vendor not in images_dict.keys():
                images_dict[image.operating_system.vendor] = [image.to_json()]
            else:
                images_dict[image.operating_system.vendor].append(image.to_json())
        sync_task.result = {"images": images_dict}
    else:
        sync_task.message = ERROR_SYNC_IMAGES
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="get_ibm_operating_systems")
def task_get_operating_systems(task_id, cloud_id, region):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    operating_systems = get_ibm_operating_systems(ibm_cloud, region)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if operating_systems:
        sync_task.status = SUCCESS
        operating_systems_dict = dict()
        for image in operating_systems:
            if image.vendor not in operating_systems_dict.keys():
                operating_systems_dict[image.vendor] = [image.to_json()]
            else:
                operating_systems_dict[image.vendor].append(image.to_json())
        sync_task.result = {"operating_systems": operating_systems_dict}
    else:
        sync_task.message = ERROR_SYNC_IMAGES
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="get_ibm_instance_profiles")
def task_get_instance_profiles(task_id, cloud_id, region):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    instance_profiles = get_ibm_instance_profiles(ibm_cloud, region)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if instance_profiles:
        sync_task.status = SUCCESS
        sync_task.result = {
            "instance_profiles": [
                instance_profile.to_json() for instance_profile in instance_profiles
            ]
        }
    else:
        sync_task.message = ERROR_SYNC_INSTANCE_PROFILES
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="get_ibm_volume_profiles")
def task_get_volume_profiles(task_id, cloud_id, region):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    volume_profiles = get_ibm_volume_profiles(ibm_cloud, region)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if volume_profiles:
        sync_task.status = SUCCESS
        sync_task.result = {
            "volume_profiles": [
                volume_profile.to_json() for volume_profile in volume_profiles
            ]
        }
    else:
        sync_task.message = ERROR_SYNC_VOLUME_PROFILES
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="configure_ibm_load_balancer", bind=True)
def task_create_ibm_load_balancer(self, data, user_id, project_id):
    time.sleep(1)
    ibm_load_balancer = configure_load_balancer(data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_load_balancer and ibm_load_balancer.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_load_balancer.id
        log_resource_billing(user_id, project_id, ibm_load_balancer)
    elif task and ibm_load_balancer:
        task.status = FAILED
        task.resource_id = ibm_load_balancer.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_load_balancers", bind=True)
def task_delete_ibm_load_balancer(self, load_balancer_id):
    time.sleep(1)
    ibm_load_balancer = IBMLoadBalancer.query.get(load_balancer_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_load_balancer(ibm_load_balancer):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_ssh_key", bind=True)
def task_create_ssh_key(self, data, user_id, project_id):
    time.sleep(1)
    ibm_ssh_key = configure_ssh_key(data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_ssh_key and ibm_ssh_key.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_ssh_key.id
        log_resource_billing(user_id, project_id, ibm_ssh_key)
    elif task and ibm_ssh_key:
        task.status = FAILED
        task.resource_id = ibm_ssh_key.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_ssh_key", bind=True)
def task_delete_ibm_ssh_key(self, ssh_key_id):
    time.sleep(1)
    ibm_ssh_key = IBMSshKey.query.get(ssh_key_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ssh_key(ibm_ssh_key):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_image", bind=True)
def task_create_ibm_image(self, data, user_id, project_id):
    time.sleep(1)
    ibm_image = configure_image(data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_image and ibm_image.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_image.id
        log_resource_billing(user_id, project_id, ibm_image)
    elif task and ibm_image:
        task.status = FAILED
        task.resource_id = ibm_image.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_image", bind=True)
def task_delete_ibm_image(self, image_id):
    time.sleep(1)
    image = IBMImage.query.get(image_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_image(image):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="fire_discovery_task", bind=True)
def task_fire_discovery(self, cloud_id):
    time.sleep(1)
    ibm_cloud = IBMCloud.query.get(cloud_id)
    ibm_dc = IBMDiscoveryClient(ibm_cloud)
    result = ibm_dc.run_discovery()
    sync_task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if sync_task and result:
        sync_task.status = SUCCESS
    elif sync_task:
        sync_task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_floating_ip", bind=True)
def task_create_floating_ip(self, data, user_id, project_id):
    time.sleep(1)
    ibm_floating_ip = configure_floating_ip(data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_floating_ip and ibm_floating_ip.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_floating_ip.id
        log_resource_billing(user_id, project_id, ibm_floating_ip)
    elif task and ibm_floating_ip:
        task.status = FAILED
        task.resource_id = ibm_floating_ip.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_ibm_floating_ips", bind=True)
def task_delete_ibm_floating_ip(self, floating_ip_id):
    time.sleep(1)
    ibm_floating_ip = IBMFloatingIP.query.get(floating_ip_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_floating_ip(ibm_floating_ip):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_vpc_address_prefix", bind=True)
def task_create_ibm_vpc_address_prefix(self, data, vpc_id, user_id, project_id):
    time.sleep(1)
    ibm_vpc_address_prefix = configure_address_prefix(data, vpc_id)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and ibm_vpc_address_prefix and ibm_vpc_address_prefix.status == CREATED:
        task.status = SUCCESS
        task.resource_id = ibm_vpc_address_prefix.id
        log_resource_billing(user_id, project_id, ibm_vpc_address_prefix)
    elif task and ibm_vpc_address_prefix:
        task.status = FAILED
        task.resource_id = ibm_vpc_address_prefix.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="delete_vpc_address_prefix", bind=True)
def task_delete_ibm_vpc_address_prefix(self, address_prefix_id):
    time.sleep(1)
    address_prefix = IBMAddressPrefix.query.get(address_prefix_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_address_prefix(address_prefix):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="get_cos_buckets")
def task_get_cos_buckets(task_id, cloud_id, region, get_objects=False, primary_objects=True):
    ibm_cloud = IBMCloud.query.get(cloud_id)
    buckets, result = get_cos_buckets(ibm_cloud, region, get_objects, primary_objects)
    sync_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not sync_task:
        return

    if result:
        sync_task.status = SUCCESS
        sync_task.result = {"buckets": buckets}
    else:
        sync_task.message = ERROR_SYNC_COS_BUCKETS
        sync_task.status = FAILED

    doosradb.session.commit()


@celery.task(name="create_ibm_route_for_vpc_network", bind=True)
def task_create_ibm_route_for_vpc_network(self, cloud_id, vpc_id, data, user_id, project_id):
    time.sleep(1)
    route = configure_ibm_vpc_route(cloud_id, vpc_id, data)
    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and route and route.status == CREATED:
        task.status = SUCCESS
        task.resource_id = route.id
        log_resource_billing(user_id, project_id, route)
    elif task and route:
        task.status = FAILED
        task.resource_id = route.id
    elif task:
        task.status = FAILED

    doosradb.session.commit()


@celery.task(name="delete_ibm_vpc_route", bind=True)
def task_delete_ibm_vpc_route_network(self, route_id):
    time.sleep(1)
    ibm_vpc_route = IBMVpcRoute.query.get(route_id)

    task = (
        doosradb.session.query(IBMTask)
        .filter_by(id=str(self.request.id).strip())
        .first()
    )
    if task and delete_ibm_vpc_route(ibm_vpc_route):
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()
