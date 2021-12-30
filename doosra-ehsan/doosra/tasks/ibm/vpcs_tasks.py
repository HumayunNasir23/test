import json
import logging

from celery import chain, chord, group

from doosra import db as doosradb
from doosra.common.consts import CREATED, CREATING, UPDATION_PENDING, SUCCESS, CREATION_PENDING
from doosra.common.consts import IN_PROGRESS
from doosra.common.utils import DELETING, DELETED
from doosra.ibm.common.billing_utils import log_resource_billing
from doosra.ibm.common.consts import FLOATING_IP_NAME, INST_START, PROVISIONING, VALIDATION
from doosra.ibm.common.report_consts import *
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.ibm.instances.utils import get_volume_name
from doosra.ibm.managers.exceptions import (
    IBMInvalidRequestError,
)
from doosra.models import (
    IBMVpcNetwork,
    IBMIKEPolicy,
    IBMVolumeProfile,
    IBMVolumeAttachment,
    IBMVolume,
    IBMFloatingIP,
    IBMNetworkInterface,
    IBMAddressPrefix,
    IBMIPSecPolicy,
    IBMNetworkAcl,
    IBMNetworkAclRule,
    IBMSshKey,
    IBMSecurityGroup,
    IBMSecurityGroupRule,
    IBMPublicGateway,
    IBMSubnet,
    IBMInstanceProfile,
    IBMInstance,
    IBMInstanceTasks,
    IBMImage,
    IBMListener,
    IBMPoolMember,
    IBMVpnGateway,
    IBMVpnConnection,
    IBMLoadBalancer,
    IBMPool,
    IBMHealthCheck,
    IBMResourceGroup,
    IBMVpcRoute,
    WorkSpace
)
from doosra.models.ibm.kubernetes_models import KubernetesCluster, KubernetesClusterWorkerPool, \
    KubernetesClusterWorkerPoolZone
from doosra.tasks.celery_app import celery
from doosra.tasks.exceptions import WorkflowTerminated, TaskFailureError
from doosra.tasks.ibm.acl_tasks import task_validate_ibm_acl, task_create_ibm_acl
from doosra.tasks.ibm.address_prefix_tasks import task_add_ibm_address_prefix
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_group_tasks, update_ibm_task
from doosra.tasks.ibm.dedicated_host_tasks import task_create_dedicated_host_workflow, task_validate_dedicated_host
from doosra.tasks.ibm.floating_ip_tasks import task_delete_ibm_floating_ip
from doosra.tasks.ibm.image_tasks import task_validate_ibm_images
from doosra.tasks.ibm.instance_tasks import task_validate_ibm_instance_profile, \
    task_validate_ibm_volumes, create_ibm_instance, task_delete_ibm_instance, instance_task_insert, create_backup
from doosra.tasks.ibm.kubernetes_tasks import task_validate_kubernetes_cluster, task_migrate_kubernetes_cluster, task_delete_ibm_k8s_cluster
from doosra.tasks.ibm.load_balancer_tasks import task_delete_ibm_load_balancer
from doosra.tasks.ibm.public_gateway_tasks import task_create_ibm_public_gateway, task_delete_public_gateway
from doosra.tasks.ibm.resource_group_tasks import task_validate_ibm_resource_group
from doosra.tasks.ibm.security_group_tasks import task_add_ibm_security_group
from doosra.tasks.ibm.ssh_key_tasks import task_validate_ibm_ssh_key, task_create_ibm_ssh_key
from doosra.tasks.ibm.subnet_tasks import task_create_ibm_subnet, task_delete_ibm_subnet, \
    task_attach_public_gateway_to_subnet
from doosra.tasks.ibm.vpn_tasks import task_create_ibm_ike_policy, task_validate_ibm_ike_policy, \
    task_validate_ibm_ipsec_policy, task_create_ibm_ipsec_policy, task_create_ibm_vpn, \
    task_configure_ibm_vpn_connection, task_delete_ibm_vpn_gateway, list_diff, \
    task_update_peer_cidr_connection, task_update_local_cidr_connection, \
    task_delete_peer_cidr_connection, task_delete_local_cidr_connection
from doosra.tasks.ibm.route_tasks import task_create_ibm_route

LOGGER = logging.getLogger("vpcs_tasks.py")


@celery.task(name="validate_ibm_vpc", base=IBMBaseTask, bind=True)
def task_validate_ibm_vpc(self, task_id, cloud_id, region, vpc_id):
    """Check if VPC with same name already exists or VPCs limit doesnt exceed"""

    ibm_vpc_network = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    self.resource_name = ibm_vpc_network.name
    self.resource_type = "vpc"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    if not ibm_vpc_network:
        return

    vpc_list = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_vpcs()
    for vpc in vpc_list:
        if vpc["name"] == ibm_vpc_network.name:
            raise IBMInvalidRequestError(
                "VPC with name '{}' already configured in region '{}'".format(ibm_vpc_network.name, self.region))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info("IBM VPC with name '{name}' validated successfully".format(name=ibm_vpc_network.name))


@celery.task(name="configure_ibm_vpc", base=IBMBaseTask, bind=True)
def task_configure_ibm_vpc(self, task_id, cloud_id, region, vpc_id):
    """Configure VPC"""

    ibm_vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not ibm_vpc:
        return

    ibm_vpc.status = CREATING
    doosradb.session.commit()
    self.resource = ibm_vpc
    self.resource_type = "vpc"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    ibm_resource_group = self.ibm_manager.resource_ops.fetch_ops.get_resource_groups(ibm_vpc.ibm_resource_group.name)
    if ibm_resource_group:
        ibm_resource_group[0].add_update_db()

    configured_vpc = configure_and_save_obj_confs(self.ibm_manager, ibm_vpc)
    ibm_vpc = ibm_vpc.make_copy()
    for acl in configured_vpc.acls.all():
        if acl.is_default:
            ibm_vpc.acls.append(acl.make_copy())

    for security_group in configured_vpc.security_groups.all():
        if security_group.is_default:
            ibm_vpc.security_groups.append(security_group.make_copy())

    for address_prefix in configured_vpc.address_prefixes.all():
        if address_prefix.is_default:
            ibm_vpc.address_prefixes.append(address_prefix.make_copy())

    ibm_vpc.status = CREATED
    ibm_vpc.resource_id = configured_vpc.resource_id
    ibm_vpc.crn = configured_vpc.crn
    ibm_vpc = ibm_vpc.make_copy().add_update_db()
    LOGGER.info(
        "IBM VPC Network with name '{name}' created successfully".format(name=ibm_vpc.name)
    )

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_vpc)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="delete_ibm_vpc", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpc(self, task_id, cloud_id, region, vpc_id):
    """Delete VPC"""

    ibm_vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not ibm_vpc:
        return

    self.resource = ibm_vpc
    ibm_vpc.status = DELETING
    doosradb.session.commit()
    workspace_id = ibm_vpc.workspace_id
    fetched_vpc = self.ibm_manager.rias_ops.fetch_ops.get_all_vpcs(name=ibm_vpc.name, required_relations=False)

    if fetched_vpc:
        self.ibm_manager.rias_ops.delete_vpc(fetched_vpc[0])

    workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
    if workspace:
        doosradb.session.delete(workspace)

    ibm_vpc.status = DELETED
    doosradb.session.delete(ibm_vpc)
    doosradb.session.commit()
    LOGGER.info("IBM VPC '{name}' successfully deleted on IBM Cloud".format(name=ibm_vpc.name))


@celery.task(name="create_ibm_vpc_workflow", base=IBMBaseTask, bind=True)
def task_create_ibm_vpc_workflow(self, task_id, cloud_id, region, data, vpc_id, softlayer_id=None):
    """
    Create the whole workflow for VPC tasks including VPC and its dependencies
    1) Validates VPC pre requisites
    2) Configure VPC and its network functions on IBM Cloud
    :return:
    """
    validation_dict, provisioning_dict = {}, {}
    validation_status, provisioning_status, report_status = PENDING, PENDING, PENDING
    ssh_keys_report_list, ike_policy_report_list, ipsec_policy_report_list = list(), list(), list()
    dedicated_hosts_report_list = list()
    kubernetes_cluster_report_list = list()
    security_group_report_list, public_gateway_report_list, address_prefix_report_list = list(), list(), list()
    subnet_report_list, attach_pg_to_subnet_report_list, instance_report_list = list(), list(), list()
    instance_profile_report_list, image_report_list, floating_ip_report_list = list(), list(), list()
    vpn_report_list, vpn_connections_report_list, volume_report_list, acl_report_list = list(), list(), list(), list()
    load_balancer_report_list, adding_local_cidr_report_list, adding_peer_cidr_report_list = list(), list(), list()
    deleting_local_cidr_report_list, deleting_peer_cidr_report_list = list(), list()
    route_report_list = list()

    # Workflow Tasks lists
    workflow_steps, validation_tasks, regional_tasks, vpc_tasks = list(), list(), list(), list()
    subnet_tasks_list, instance_vpns_tasks_list, vpn_connections_task_list = list(), list(), list()
    load_balancer_tasks_list, floating_ip_tasks_list = list(), list()
    route_tasks_list = list()
    kubernetes_cluster_task_list = list()

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        raise WorkflowTerminated("IBMVpcNetwork with ID {id} not found".format(id=vpc_id))

    ibm_vpc_report = vpc.to_report_json()
    provisioning_dict.update(ibm_vpc_report)
    validation_dict.update(ibm_vpc_report)
    request_metadata = {
        "instances": [], "ssh_keys": [], "vpn_gateways": [], "ike_policies": [], "ipsec_policies": [], "acls": [],
        "security_groups": [], "load_balancers": [], "routes": [], "dedicated_hosts": [], "kubernetes_clusters": []
    }
    vpc = vpc.make_copy()
    ibm_resource_group = IBMResourceGroup(name=data["resource_group"], cloud_id=cloud_id)
    ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
    vpc.ibm_resource_group = ibm_resource_group.make_copy()
    vpc = vpc.add_update_db()
    validation_dict.update(ibm_resource_group.to_report_json(vpc.status))

    if not vpc.status == CREATED:
        validation_tasks.append(
            task_validate_ibm_vpc.si(task_id=task_id, cloud_id=cloud_id, region=region, vpc_id=vpc.id))
        validation_tasks.append(task_validate_ibm_resource_group.si(
            task_id=task_id, cloud_id=cloud_id, region=region, resource_group=data["resource_group"]))

    # SSH key validation and configuration tasks
    for ssh_key in data.get("ssh_keys", []):
        if not ssh_key.get("is_provisioning"):
            request_metadata["ssh_keys"].append(ssh_key)
            continue
        ibm_ssh_key = self.cloud.ssh_keys.filter(
            IBMSshKey.name == ssh_key["name"], IBMSshKey.public_key == ssh_key["public_key"].strip(),
            IBMSshKey.status == CREATED, IBMSshKey.region == self.region).first()
        if ibm_ssh_key:
            continue

        ibm_ssh_key = IBMSshKey(
            name=ssh_key["name"], public_key=ssh_key["public_key"], type_="rsa", region=region, cloud_id=cloud_id)
        ibm_ssh_key = ibm_ssh_key.add_update_db()
        ssh_keys_report_list.append(ibm_ssh_key.to_report_json())

        validation_tasks.append(task_validate_ibm_ssh_key.si(
            task_id=task_id, cloud_id=cloud_id, region=region, ssh_key=ssh_key))
        regional_tasks.append(task_create_ibm_ssh_key.si(
            task_id=task_id, cloud_id=cloud_id, region=region, ssh_key_id=ibm_ssh_key.id,
            resource_group=data["resource_group"]))

    # Dedicated Host validation and configuration tasks
    all_dhs_created = True
    for dedicated_host in data.get("dedicated_hosts", []):
        if not dedicated_host.get("is_provisioning"):
            request_metadata["dedicated_hosts"].append(dedicated_host.copy())
            continue

        all_dhs_created = False
        dedicated_hosts_report_list.append(
            {
                "name": dedicated_host["name"],
                "status": "PENDING",
                "message": ""
            }
        )
        validation_tasks.append(
            task_validate_dedicated_host.si(task_id=task_id, cloud_id=cloud_id, region=region, data=dedicated_host))

        vpc_tasks.append(
            task_create_dedicated_host_workflow.si(
                task_id=task_id, cloud_id=cloud_id, region=region, data=dedicated_host,
                workspace_id=vpc.workspace.id if vpc.workspace else None
            )
        )

    # IKE Policy validation and configuration tasks
    for ike_policy in data.get("ike_policies", []):
        if not ike_policy.get("is_provisioning"):
            request_metadata["ike_policies"].append(ike_policy)
            continue

        ibm_ike_policy = IBMIKEPolicy(
            name=ike_policy["name"], region=region, key_lifetime=ike_policy["key_lifetime"],
            authentication_algorithm=ike_policy["authentication_algorithm"],
            encryption_algorithm=ike_policy["encryption_algorithm"], ike_version=ike_policy["ike_version"],
            dh_group=ike_policy["dh_group"], cloud_id=cloud_id)
        ibm_ike_policy.ibm_resource_group = vpc.ibm_resource_group.make_copy()
        ibm_ike_policy = ibm_ike_policy.make_copy().add_update_db()
        ike_policy_report_list.append(ibm_ike_policy.to_report_json())

        validation_tasks.append(
            task_validate_ibm_ike_policy.si(task_id=task_id, cloud_id=cloud_id, region=region, ike_policy=ike_policy))
        regional_tasks.append(task_create_ibm_ike_policy.si(
            task_id=task_id, cloud_id=cloud_id, region=region, ike_policy_id=ibm_ike_policy.id))

    # IPSec Policy Validation and Configuration Tasks
    for ipsec_policy in data.get("ipsec_policies", []):
        if not ipsec_policy.get("is_provisioning"):
            request_metadata["ipsec_policies"].append(ipsec_policy)
            continue

        ibm_ipsec_policy = IBMIPSecPolicy(
            name=ipsec_policy["name"], region=region, key_lifetime=ipsec_policy["key_lifetime"],
            authentication_algorithm=ipsec_policy["authentication_algorithm"],
            encryption_algorithm=ipsec_policy["encryption_algorithm"], pfs_dh_group=ipsec_policy.get("pfs"),
            cloud_id=cloud_id)
        ibm_ipsec_policy.ibm_resource_group = vpc.ibm_resource_group.make_copy()
        ibm_ipsec_policy = ibm_ipsec_policy.make_copy().add_update_db()
        ipsec_policy_report_list.append(ibm_ipsec_policy.to_report_json())

        validation_tasks.append(task_validate_ibm_ipsec_policy.si(
            task_id=task_id, cloud_id=cloud_id, region=region, ipsec_policy=ipsec_policy))
        regional_tasks.append(task_create_ibm_ipsec_policy.si(
            task_id=task_id, cloud_id=cloud_id, region=region, ipsec_policy_id=ibm_ipsec_policy.id))

    # ACL validation and configuration tasks
    for acl in data.get("acls", []):
        if not acl.get("is_provisioning"):
            request_metadata["acls"].append(acl)
            continue

        ibm_acl = IBMNetworkAcl(name=acl["name"], region=region, cloud_id=self.cloud.id, is_default=False)
        for rule in acl["rules"]:
            ibm_rule = IBMNetworkAclRule(
                name=rule["name"], action=rule["action"], destination=rule.get("destination"),
                direction=rule["direction"], source=rule.get("source"), protocol=rule["protocol"],
                port_max=rule.get("destination_port_max"), port_min=rule.get("destination_port_min"),
                source_port_max=rule.get("source_port_max"), source_port_min=rule.get("source_port_min"),
                code=rule.get("code"), type_=rule.get("type"))
            ibm_acl.rules.append(ibm_rule)

        ibm_acl = ibm_acl.add_update_db(vpc)
        acl_report_list.append(ibm_acl.to_report_json())

        validation_tasks.append(
            task_validate_ibm_acl.si(task_id=task_id, cloud_id=cloud_id, region=region, vpc_name=vpc.name, acl=acl))
        regional_tasks.append(
            task_create_ibm_acl.si(task_id=task_id, cloud_id=cloud_id, region=region, acl_id=ibm_acl.id,
                                   resource_group=data["resource_group"]))

    # Security Group validation and configuration tasks
    for security_group in data.get("security_groups", []):
        if not security_group.get("is_provisioning"):
            request_metadata["security_groups"].append(security_group)
            continue

        ibm_security_group = IBMSecurityGroup(name=security_group["name"], cloud_id=cloud_id, region=region)
        for rule in security_group.get("rules", []):
            ibm_security_group_rule = IBMSecurityGroupRule(
                rule["direction"], rule["protocol"], rule.get("code"), rule.get("type"), rule.get("port_min"),
                rule.get("port_max"), rule.get("address"), rule.get("cidr_block"))

            if rule.get("security_group"):
                ibm_security_group_rule.rule_type = "security-group"

            ibm_security_group.rules.append(ibm_security_group_rule)
        ibm_security_group.ibm_resource_group = vpc.ibm_resource_group.make_copy()
        ibm_security_group = ibm_security_group.make_copy().add_update_db(vpc)
        security_group_report_list.append(ibm_security_group.to_report_json())

        vpc_tasks.append(task_add_ibm_security_group.si(
            task_id=task_id, cloud_id=cloud_id, region=region, security_group_id=ibm_security_group.id))

    # Public Gateway Validation an Configuration Tasks
    for public_gateway in data.get("public_gateways", []):
        ibm_public_gateway = IBMPublicGateway(
            name=public_gateway["name"], zone=public_gateway["zone"], cloud_id=cloud_id, region=region)
        ibm_public_gateway = ibm_public_gateway.make_copy().add_update_db(vpc)

        public_gateway_report_list.append(ibm_public_gateway.to_report_json())

        vpc_tasks.append(
            task_create_ibm_public_gateway.si(
                task_id=task_id, cloud_id=cloud_id, region=region, public_gateway_id=ibm_public_gateway.id,
                resource_group=data["resource_group"]
            ))

    # Address Prefix Validation and Configuration Tasks
    for address_prefix in data.get("address_prefixes", []):
        ibm_address_prefix = IBMAddressPrefix(
            name=address_prefix.get("name"), zone=address_prefix["zone"], address=address_prefix["address"],
            is_default=address_prefix.get("is_default"))
        ibm_address_prefix = ibm_address_prefix.make_copy().add_update_db(vpc)

        if address_prefix["is_default"]:
            ibm_address_prefix.status = CREATED
            doosradb.session.commit()
            continue

        address_prefix_report_list.append(ibm_address_prefix.to_report_json())
        vpc_tasks.append(task_add_ibm_address_prefix.si(
            task_id=task_id, cloud_id=cloud_id, region=region, addr_prefix_id=ibm_address_prefix.id))

    # Subnet Validation and Configuration Tasks
    for subnet in data.get("subnets", []):
        if subnet.get("is_updating"):
            ibm_subnet = doosradb.session.query(IBMSubnet).filter_by(
                name=subnet["name"], zone=subnet["zone"], vpc_id=vpc_id).first()
            if not ibm_subnet:
                raise WorkflowTerminated("IBM Subnet with name {name} not found".format(name=subnet["name"]))

            if subnet.get("public_gateway"):
                ibm_subnet = ibm_subnet.make_copy()
                ibm_subnet.ibm_public_gateway = vpc.public_gateways.filter(
                    IBMPublicGateway.name == subnet["public_gateway"],
                    IBMPublicGateway.zone == subnet["zone"]).first().make_copy()

                ibm_subnet = ibm_subnet.make_copy().add_update_db(vpc)
                ibm_subnet.status = UPDATION_PENDING
                doosradb.session.commit()

                attach_pg_to_subnet_report_list.append(
                    ibm_subnet.to_report_json(public_gateway=subnet["public_gateway"]))
                subnet_tasks_list.append(
                    task_attach_public_gateway_to_subnet.si(
                        task_id=task_id, cloud_id=cloud_id, region=region, subnet_id=ibm_subnet.id,
                        public_gateway_id=ibm_subnet.ibm_public_gateway.id))
            continue

        ibm_subnet = IBMSubnet(
            name=subnet["name"], zone=subnet["zone"], ipv4_cidr_block=subnet["ip_cidr_block"], cloud_id=cloud_id,
            region=region)
        ibm_subnet.ibm_address_prefix = vpc.address_prefixes.filter(
            IBMAddressPrefix.name == subnet["address_prefix"],
            IBMAddressPrefix.zone == subnet["zone"]).first().make_copy()

        if subnet.get("public_gateway"):
            ibm_subnet.ibm_public_gateway = vpc.public_gateways.filter(
                IBMPublicGateway.name == subnet["public_gateway"],
                IBMPublicGateway.zone == subnet["zone"]).first().make_copy()

        if subnet.get("network_acl"):
            ibm_subnet.network_acl = vpc.acls.filter(
                IBMNetworkAcl.name == subnet["network_acl"]["name"]).first().make_copy()

        ibm_subnet = ibm_subnet.make_copy().add_update_db(vpc)
        subnet_report_list.append(ibm_subnet.to_report_json())

        subnet_tasks_list.append(
            task_create_ibm_subnet.si(task_id=task_id, cloud_id=cloud_id, region=region, subnet_id=ibm_subnet.id,
                                      resource_group=data["resource_group"]))

        # Routes Configuration Tasks
        for route in data.get("routes", []):
            ibm_route = IBMVpcRoute(name=route.get("name"), region=vpc.region, zone=route["zone"],
                                    destination=route.get("destination"),
                                    next_hop_address=route.get("next_hop_address"), cloud_id=cloud_id)
            ibm_route = ibm_route.make_copy().add_update_db(vpc)

            route_report_list.append(ibm_route.to_report_json())
            route_tasks_list.append(task_create_ibm_route.si(
                task_id=task_id, cloud_id=cloud_id, region=region, route_id=ibm_route.id))

    # Kubernetes Clusters Validation and Configuration Tasks
    for kubernetes_cluster in data.get("kubernetes_clusters", []):
        if not kubernetes_cluster.get("is_provisioning"):
            request_metadata["kubernetes_clusters"].append(kubernetes_cluster)
            continue

        k8s_cluster = KubernetesCluster(name=kubernetes_cluster.get("name"),
                                        kube_version=kubernetes_cluster.get("kube_version"),
                                        disable_public_service_endpoint=False,
                                        provider="vpc-gen2",
                                        pod_subnet=kubernetes_cluster.get("pod_subnet"),
                                        service_subnet=kubernetes_cluster.get("service_subnet"),
                                        status=CREATION_PENDING,
                                        vpc_id=vpc.id,
                                        cloud_id=self.cloud.id
                                        )
        k8s_cluster.is_workspace = True
        k8s_cluster.ibm_resource_group = vpc.ibm_resource_group.make_copy()
        for worker_pool in kubernetes_cluster['worker_pools']:
            kubernetes_cluster_worker_pool = KubernetesClusterWorkerPool(
                name=worker_pool.get("name"), disk_encryption=worker_pool.get("disk_encryption"),
                flavor=worker_pool["flavor"], worker_count=worker_pool["worker_count"]
            )

            for worker_pool_zone in worker_pool['zones']:
                kubernetes_cluster_worker_pool_zone = KubernetesClusterWorkerPoolZone(name=worker_pool_zone["zone"])
                ibm_subnet = vpc.subnets.filter(IBMSubnet.name == worker_pool_zone['subnets'][0]).first()
                kubernetes_cluster_worker_pool_zone.subnets.append(ibm_subnet.make_copy())
                kubernetes_cluster_worker_pool.zones.append(kubernetes_cluster_worker_pool_zone)
            k8s_cluster.worker_pools.append(kubernetes_cluster_worker_pool)
        k8s_cluster = k8s_cluster.make_copy().add_update_db(vpc)

        kubernetes_cluster_report = k8s_cluster.to_report_json()
        kubernetes_migration_report = self.report_utils.get_cluster_migration_steps()
        if kubernetes_migration_report:
            kubernetes_cluster_report.update(kubernetes_migration_report)
        kubernetes_cluster_report_list.append(kubernetes_cluster_report)

        validation_tasks.append(
            task_validate_kubernetes_cluster.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                                cluster_id=k8s_cluster.id))

        kubernetes_cluster_task_list.append(task_migrate_kubernetes_cluster.si(
            task_id=task_id, cloud_id=cloud_id, region=region, cluster_id=k8s_cluster.id,
            source_cluster=kubernetes_cluster['resource_id'], softlayer_id=softlayer_id))

    # Validation and Configuration Tasks for Instances
    for instance in data.get("instances", []):
        if not instance.get("is_provisioning"):
            request_metadata["instances"].append(instance)
            continue

        ibm_instance = IBMInstance(
            name=instance["name"], zone=instance["zone"], user_data=instance.get("user_data"),
            cloud_id=self.cloud.id, state=INST_START, region=region, is_volume_migration=instance.get("data_migration"),
            instance_type=instance.get("instance_type"), data_center=instance.get("data_center"),
            auto_scale_group=instance.get("auto_scale_group"),
            original_operating_system_name=instance.get("original_operating_system_name"))

        windows_ = [instance.get("original_operating_system_name"), instance.get("original_image"),
                    instance["image"].get("vpc_image_name"), instance["image"].get("public_image")]
        windows = [wind.upper() for wind in windows_ if wind]
        windows_backup = "WINDOWS" in windows[0] if windows else False

        ibm_instance_report = ibm_instance.to_report_json()
        migration_report = self.report_utils.get_migration_steps(
            image_location=instance["image"].get("image_location"), data_migration=instance.get("data_migration"),
            windows_backup=windows_backup)
        if migration_report:
            ibm_instance_report.update(migration_report)
        instance_report_list.append(ibm_instance_report)

        ibm_instance_profile = IBMInstanceProfile(name=instance["instance_profile"], cloud_id=cloud_id)
        ibm_instance_profile = ibm_instance_profile.get_existing_from_db() or ibm_instance_profile
        ibm_instance.ibm_instance_profile = ibm_instance_profile.make_copy()
        ibm_instance.ibm_resource_group = vpc.ibm_resource_group.make_copy()
        ibm_instance = ibm_instance.make_copy().add_update_db(vpc)
        ibm_instance = ibm_instance.make_copy()
        ibm_instance_profile_report = ibm_instance_profile.to_report_json()
        if ibm_instance_profile_report not in instance_profile_report_list:
            instance_profile_report_list.append(ibm_instance_profile_report)

        ibm_image = None
        if instance['image'].get('image_location') in {IBMInstanceTasks.LOCATION_CLASSICAL_VSI,
                                                       IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE,
                                                       IBMInstanceTasks.LOCATION_COS_VHD,
                                                       IBMInstanceTasks.LOCATION_COS_VMDK,
                                                       IBMInstanceTasks.LOCATION_COS_QCOW2,
                                                       }:
            ibm_image = IBMImage(name=ibm_instance.name, region=region, cloud_id=self.cloud.id, visibility="private",
                                 vpc_image_name=instance['image'].get('vpc_image_name') or instance["image"].get(
                                     "public_image"))

        elif instance['image'].get('image_location') == IBMInstanceTasks.LOCATION_CUSTOM_IMAGE:
            ibm_image = IBMImage(name=instance['image'].get('custom_image'), region=region, cloud_id=self.cloud.id,
                                 visibility="private")

        elif instance['image'].get('image_location') == IBMInstanceTasks.LOCATION_PUBLIC_IMAGE:
            ibm_image = IBMImage(name=instance['image'].get('public_image'), region=region, cloud_id=self.cloud.id,
                                 visibility="public")

        ibm_image.ibm_resource_group = vpc.ibm_resource_group.make_copy()
        existing_image = ibm_image.get_existing_from_db()
        if existing_image:
            existing_image = existing_image.make_copy()
        ibm_instance.ibm_image = existing_image or ibm_image
        ibm_instance = ibm_instance.add_update_db(vpc)
        ibm_instance = ibm_instance.make_copy()

        validation_tasks.append(task_validate_ibm_instance_profile.si(
            task_id=task_id, cloud_id=cloud_id, region=region, instance_profile=instance["instance_profile"]))

        for ssh_key in instance.get("ssh_keys", []):
            ibm_ssh_key = self.cloud.ssh_keys.filter(
                IBMSshKey.name == ssh_key["name"], IBMSshKey.region == self.region).first()
            if not ibm_ssh_key:
                raise WorkflowTerminated("IBM SSH key '{}' not found in region '{}' with cloud_id '{}'".format(
                    ssh_key["name"], self.region, self.cloud.id))

            ibm_instance.ssh_keys.append(ibm_ssh_key.make_copy())
            if not ibm_ssh_key.status == CREATED and ibm_ssh_key.name not in [
                ssh_key_["name"] for ssh_key_ in data.get("ssh_keys", [])]:
                ibm_ssh_key_report = ibm_ssh_key.to_report_json()
                if ibm_ssh_key_report not in ssh_keys_report_list:
                    ssh_keys_report_list.append(ibm_ssh_key_report)

                validation_tasks.append(task_validate_ibm_ssh_key.si(
                    task_id=task_id, cloud_id=cloud_id, region=region,
                    ssh_key={"public_key": ibm_ssh_key.public_key,
                             "name": ibm_ssh_key.name}))
                regional_tasks.append(task_create_ibm_ssh_key.si(
                    task_id=task_id, cloud_id=cloud_id, region=region, ssh_key_id=ibm_ssh_key.id))

        for index, network_interface in enumerate(instance.get("network_interfaces", [])):
            ibm_network_interface = IBMNetworkInterface(
                name=network_interface["name"],
                is_primary=network_interface["is_primary"])
            ibm_network_interface.ibm_subnet = (
                vpc.subnets.filter(IBMSubnet.name == network_interface["subnet"]).first().make_copy())

            if network_interface.get("security_groups"):
                for sec_group in network_interface["security_groups"]:
                    ibm_security_group = vpc.security_groups.filter(IBMSecurityGroup.name == sec_group).first()
                    if not ibm_security_group:
                        raise WorkflowTerminated(
                            "IBMSecurityGroup with name {name} not found in region {region} in DB".format(
                                name=sec_group, region=region))

                    ibm_network_interface.security_groups.append(ibm_security_group.make_copy())

            if network_interface.get("reserve_floating_ip"):
                floating_ip = instance["name"][13:] if len(instance["name"]) > 50 else instance["name"]
                ibm_floating_ip = IBMFloatingIP(
                    name=FLOATING_IP_NAME.format(floating_ip, index),
                    region=region,
                    zone=ibm_instance.zone,
                    cloud_id=cloud_id,
                )
                ibm_resource_group = IBMResourceGroup(name=data["resource_group"], cloud_id=cloud_id)
                ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
                ibm_floating_ip.ibm_resource_group = ibm_resource_group

                ibm_floating_ip = ibm_floating_ip.add_update_db()
                floating_ip_report_list.append(ibm_floating_ip.to_report_json())
                ibm_network_interface.floating_ip = ibm_floating_ip.make_copy()

            ibm_instance.network_interfaces.append(ibm_network_interface)

        for volume_attachment in instance.get("volume_attachments", list()):
            ibm_volume_attachment = IBMVolumeAttachment(
                name=volume_attachment["name"],
                type_=volume_attachment.get("type") or "data",
                is_delete=volume_attachment["is_delete"],
                is_migration_enabled=volume_attachment.get("is_migration_enabled"),
                volume_index=volume_attachment.get("volume_index")
            )
            ibm_volume = IBMVolume(
                name=volume_attachment["volume"]["name"],
                capacity=volume_attachment["volume"].get("capacity") or 100,
                zone=instance["zone"],
                region=region,
                iops=volume_attachment.get("iops") or 3000,
                encryption=instance.get("encryption") or "provider_managed",
                cloud_id=self.cloud.id,
                original_capacity=volume_attachment["volume"].get("original_capacity")

            )

            volume_profile = IBMVolumeProfile(
                name=volume_attachment["volume"]["profile"].get("name") or "custom", region=self.region,
                cloud_id=cloud_id)

            volume_profile = volume_profile.get_existing_from_db() or volume_profile
            ibm_volume.volume_profile = volume_profile.make_copy()
            ibm_volume_attachment.volume = ibm_volume
            ibm_instance.volume_attachments.append(ibm_volume_attachment)

            ibm_volume_report = ibm_volume.to_report_json()
            if ibm_volume_report not in volume_report_list:
                volume_report_list.append(ibm_volume_report)

            # TODO we should remove validation and add +1 in the volume
            validation_tasks.append(
                task_validate_ibm_volumes.si(
                    task_id=task_id, cloud_id=cloud_id, region=region, volume=volume_attachment["volume"]))

        ibm_volume = IBMVolume(
            name=get_volume_name(instance["name"]),
            capacity=100,
            zone=instance["zone"],
            region=region,
            iops=3000,
            encryption="provider_managed",
            cloud_id=self.cloud.id,
        )
        ibm_boot_volume_attachment = IBMVolumeAttachment(
            name=get_volume_name(instance["name"]),
            type_="boot",
            is_delete=True,
        )
        volume_profile = IBMVolumeProfile(name="general-purpose", region=region, cloud_id=cloud_id)
        volume_profile = volume_profile.get_existing_from_db() or volume_profile
        ibm_volume.volume_profile = volume_profile.make_copy()
        ibm_boot_volume_attachment.volume = ibm_volume
        ibm_instance.volume_attachments.append(ibm_boot_volume_attachment)
        ibm_instance = ibm_instance.make_copy().add_update_db(vpc)

        if instance["image"].get("public_image") or instance["image"].get("vpc_image_name"):
            image_name = (
                instance["image"]["public_image"]
                if instance["image"].get("public_image")
                else None or instance["image"].get("vpc_image_name")
                if instance["image"].get("vpc_image_name")
                else None
            )
            validation_tasks.append(
                task_validate_ibm_images.si(
                    task_id=task_id,
                    cloud_id=cloud_id,
                    region=region,
                    image_name=image_name
                )
            )
            image_report = {
                "name": '{image_name}'.format(image_name=image_name), "status": PENDING,
                "message": ""
            }

            if image_report not in image_report_list:
                image_report_list.append(image_report)

        ibm_instance_task_id = instance_task_insert(task_id=task_id, cloud_id=cloud_id, instance_id=ibm_instance.id,
                                                    instance=instance)

        if windows_backup and instance['image'].get(
                'image_location') == IBMInstanceTasks.LOCATION_CLASSICAL_VSI:
            ibm_instance_task = IBMInstanceTasks.query.get(ibm_instance_task_id)
            if not ibm_instance_task:
                raise TaskFailureError(f"IBMInstanceTasks {ibm_instance_task_id} deleted from db...")
            ibm_instance_task.backup_req_json = {"instance_data": instance, "step": 1,
                                                 "ibm_instance_id": ibm_instance.id, "backup": True}
            doosradb.session.commit()

            instance_vpns_tasks_list.append(
                create_backup.si(ibm_instance_task_id=ibm_instance_task_id, task_id=task_id, cloud_id=cloud_id,
                                 region=region, in_focus=True))
        else:
            instance_vpns_tasks_list.append(
                create_ibm_instance.si(task_id=task_id, cloud_id=cloud_id, region=region, instance_id=ibm_instance.id,
                                       instance=instance, ibm_instance_task_id=ibm_instance_task_id))

    for vpn in data.get("vpns", []):
        if vpn.get("is_updating"):
            for connection in vpn["connections"]:
                if not connection.get("is_updating"):
                    continue

                vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(id=vpn["id"]).first()
                vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(
                    id=connection["id"]).first().make_copy()
                local_cidrs = json.loads(vpn_connection.local_cidrs)
                peer_cidrs = json.loads(vpn_connection.peer_cidrs)

                local_cidrs_to_set = list_diff(connection["local_cidrs"], local_cidrs)
                local_cidrs_to_remove = list_diff(local_cidrs, connection["local_cidrs"])

                peer_cidrs_to_set = list_diff(connection["peer_cidrs"], peer_cidrs)
                peer_cidrs_to_remove = list_diff(peer_cidrs, connection["peer_cidrs"])
                vpn_connection.local_cidrs = json.dumps(connection["local_cidrs"])
                vpn_connection.peer_cidrs = json.dumps(connection["peer_cidrs"])
                vpn_connection.add_update_db(vpn_gateway)
                # Todo add first then delete and also has some incosistency in addin address
                # havve to discuss with maimoona about that
                for local_cidr in local_cidrs_to_set or []:
                    prefix = local_cidr.split("/")
                    instance_vpns_tasks_list.append(task_update_local_cidr_connection.si(
                        task_id=task_id, cloud_id=cloud_id, region=region, prefix=prefix[0],
                        prefix_length=prefix[1], gateway_resource_id=vpn_gateway.resource_id,
                        connection_id=connection["id"])
                    )
                    adding_local_cidr_report_list.append({
                        "name": '{local_cidr}'.format(local_cidr=local_cidr), "vpn": "{vpn}".format(vpn=vpn["name"]),
                        "vpn_connection": "{vpn_connection}".format(vpn_connection=connection["name"]),
                        "status": PENDING, "message": ""
                    })

                for peer_cidr in peer_cidrs_to_set or []:
                    prefix = peer_cidr.split("/")
                    instance_vpns_tasks_list.append(task_update_peer_cidr_connection.si(
                        task_id=task_id, cloud_id=cloud_id, region=region, prefix=prefix[0], prefix_length=prefix[1],
                        gateway_resource_id=vpn_gateway.resource_id, connection_id=connection["id"]
                    ))
                    adding_peer_cidr_report_list.append({
                        "name": '{peer_cidr}'.format(peer_cidr=peer_cidr), "vpn": "{vpn}".format(vpn=vpn["name"]),
                        "vpn_connection": "{vpn_connection}".format(vpn_connection=connection["name"]),
                        "status": PENDING, "message": ""
                    })

                for local_cidr in local_cidrs_to_remove or []:
                    prefix = local_cidr.split("/")
                    vpn_connections_task_list.append(task_delete_local_cidr_connection.si(
                        task_id=task_id, cloud_id=cloud_id, region=region, prefix=prefix[0], prefix_length=prefix[1],
                        gateway_resource_id=vpn_gateway.resource_id, connection_id=connection["id"]
                    ))
                    deleting_local_cidr_report_list.append({
                        "name": '{local_cidr}'.format(local_cidr=local_cidr), "vpn": "{vpn}".format(vpn=vpn["name"]),
                        "vpn_connection": "{vpn_connection}".format(vpn_connection=connection["name"]),
                        "status": PENDING, "message": ""
                    })

                for peer_cidr in peer_cidrs_to_remove or []:
                    prefix = peer_cidr.split("/")
                    vpn_connections_task_list.append(task_delete_peer_cidr_connection.si(
                        task_id=task_id, cloud_id=cloud_id, region=region, prefix=prefix[0], prefix_length=prefix[1],
                        gateway_resource_id=vpn_gateway.resource_id, connection_id=connection["id"]
                    ))
                    deleting_peer_cidr_report_list.append({
                        "name": '{peer_cidr}'.format(peer_cidr=peer_cidr), "vpn": "{vpn}".format(vpn=vpn["name"]),
                        "vpn_connection": "{vpn_connection}".format(vpn_connection=connection["name"]),
                        "status": PENDING, "message": ""
                    })

        if not vpn.get("is_provisioning"):
            request_metadata["vpn_gateways"].append(vpn)
            continue

        ibm_vpn_gateway = IBMVpnGateway(
            name=vpn["name"], region=region, cloud_id=cloud_id)

        ibm_vpn_gateway.ibm_subnet = vpc.subnets.filter(IBMSubnet.name == vpn["subnet"]).first().make_copy()
        for connection in vpn["connections"]:
            ibm_vpn_connection = IBMVpnConnection(
                name=connection["name"],
                peer_address=connection["peer_address"],
                pre_shared_key=connection.get("pre_shared_secret"),
                local_cidrs=json.dumps(connection["local_cidrs"]),
                peer_cidrs=json.dumps(connection["peer_cidrs"]),
                dpd_interval=connection.get("dead_peer_detection").get("interval")
                if connection.get("dead_peer_detection") else None,
                dpd_timeout=connection.get("dead_peer_detection").get("timeout")
                if connection.get("dead_peer_detection") else None,
                dpd_action=connection.get("dead_peer_detection").get("action")
                if connection.get("dead_peer_detection") else None,
                discovered_local_cidrs=connection.get("discovered_local_cidrs"),
                authentication_mode="psk"
            )

            if connection.get("ike_policy"):
                ibm_ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(
                    name=connection["ike_policy"], cloud_id=cloud_id, region=region).first().make_copy()

                if not ibm_ike_policy.status == CREATED and ibm_ike_policy.name not in [
                    ike_policy_["name"] for ike_policy_ in data.get("ike_policies", [])]:
                    ibm_ike_policy_report = ibm_ike_policy.to_report_json()
                    if ibm_ike_policy_report not in ike_policy_report_list:
                        ike_policy_report_list.append(ibm_ike_policy_report)

                    validation_tasks.append(
                        task_validate_ibm_ike_policy.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                                        ike_policy={"name": connection.get("ike_policy")}))
                    regional_tasks.append(task_create_ibm_ike_policy.si(
                        task_id=task_id, cloud_id=cloud_id, region=region, ike_policy_id=ibm_ike_policy.id))

                ibm_vpn_connection.ibm_ike_policy = ibm_ike_policy

            if connection.get("ipsec_policy"):
                ibm_ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(
                    name=connection["ipsec_policy"], cloud_id=cloud_id, region=region).first().make_copy()

                if not ibm_ipsec_policy.status == CREATED and ibm_ipsec_policy.name not in [
                    ipsec_policy_["name"] for ipsec_policy_ in data.get("ipsec_policies", [])]:
                    ibm_ipsec_policy_report = ibm_ipsec_policy.to_report_json()
                    if ibm_ipsec_policy_report not in ipsec_policy_report_list:
                        ipsec_policy_report_list.append(ibm_ipsec_policy_report)

                    validation_tasks.append(task_validate_ibm_ipsec_policy.si(
                        task_id=task_id, cloud_id=cloud_id, region=region,
                        ipsec_policy={"name": connection.get("ipsec_policy")}))
                    regional_tasks.append(task_create_ibm_ipsec_policy.si(
                        task_id=task_id, cloud_id=cloud_id, region=region, ipsec_policy_id=ibm_ipsec_policy.id))

                ibm_vpn_connection.ibm_ipsec_policy = ibm_ipsec_policy

            ibm_vpn_gateway.vpn_connections.append(ibm_vpn_connection)

        ibm_vpn_gateway.ibm_resource_group = vpc.ibm_resource_group.make_copy()
        ibm_vpn_gateway.ibm_vpc_network = vpc.make_copy()
        ibm_vpn_gateway = ibm_vpn_gateway.make_copy().add_update_db(vpc)

        for connection in ibm_vpn_gateway.vpn_connections.all():
            vpn_connections_report_list.append(connection.to_report_json(vpn=ibm_vpn_gateway.name))

            vpn_connections_task_list.append(
                task_configure_ibm_vpn_connection.si(
                    task_id=task_id, cloud_id=cloud_id, region=region, vpn_connection_id=connection.id,
                    resource_group=data["resource_group"]))

        vpn_report_list.append(ibm_vpn_gateway.to_report_json())
        instance_vpns_tasks_list.append(
            task_create_ibm_vpn.si(
                task_id=task_id, cloud_id=cloud_id, region=region, vpn_id=ibm_vpn_gateway.id))

    for load_balancer in data.get("load_balancers", []):
        if not load_balancer.get("is_provisioning"):
            request_metadata["load_balancers"].append(load_balancer)
            continue

        ibm_load_balancer = IBMLoadBalancer(
            name=load_balancer["name"], is_public=load_balancer["is_public"], region=region, vpc_id=vpc_id,
            cloud_id=cloud_id)
        ibm_load_balancer.ibm_resource_group = vpc.ibm_resource_group.make_copy()

        for subnet in load_balancer.get("subnets", []):
            ibm_subnet = vpc.subnets.filter(IBMSubnet.name == subnet).first()
            ibm_load_balancer.subnets.append(ibm_subnet.make_copy())

        pools_list = list()
        for pool in load_balancer.get("pools", []):
            ibm_pool = IBMPool(
                name=pool["name"], algorithm=pool["algorithm"], protocol=pool["protocol"],
                session_persistence=pool.get("session_persistence"))

            if pool.get("health_monitor"):
                health_check = pool["health_monitor"]
                ibm_health_check = IBMHealthCheck(
                    delay=health_check.get("delay"), max_retries=health_check.get("max_retries"),
                    timeout=health_check.get("timeout"), type_=health_check.get("protocol"),
                    url_path=health_check.get("url_path"), port=health_check.get("port"))
                ibm_pool.health_check = ibm_health_check

            for member in pool.get("members", []):
                ibm_pool_mem = IBMPoolMember(port=member.get("port"), weight=member.get("weight"))
                instance_obj = vpc.instances.filter(IBMInstance.name == member["instance"]).first()
                if instance_obj:
                    ibm_pool_mem.instance = instance_obj.make_copy()
                    ibm_pool.pool_members.append(ibm_pool_mem)

            pools_list.append(ibm_pool)
            ibm_load_balancer.pools.append(ibm_pool)

        for listener in load_balancer.get("listeners", []):
            ibm_listener = IBMListener(
                port=listener["port"], protocol=listener["protocol"], limit=listener.get("connection_limit"))

            if listener.get("default_pool"):
                ibm_listener.ibm_pool = [pool for pool in pools_list if pool.name == listener["default_pool"]][0]

            ibm_load_balancer.listeners.append(ibm_listener)

        ibm_load_balancer = ibm_load_balancer.make_copy().add_update_db(vpc)
        ibm_load_balancer.base_task_id = task_id
        doosradb.session.commit()
        load_balancer_report_list.append(ibm_load_balancer.to_report_json())

    if ssh_keys_report_list:
        SSH_KEY_REPORT_TEMPLATE[SSH_KEY_KEY][RESOURCES_KEY] = ssh_keys_report_list
        validation_dict.update(SSH_KEY_REPORT_TEMPLATE)
        provisioning_dict.update(SSH_KEY_REPORT_TEMPLATE)

    if dedicated_hosts_report_list:
        DEDICATED_HOST_REPORT_TEMPLATE[DEDICATED_HOST_KEY][RESOURCES_KEY] = dedicated_hosts_report_list
        if all_dhs_created:
            DEDICATED_HOST_REPORT_TEMPLATE[DEDICATED_HOST_KEY][STATUS_KEY] = SUCCESS
        validation_dict.update(DEDICATED_HOST_REPORT_TEMPLATE)
        provisioning_dict.update(DEDICATED_HOST_REPORT_TEMPLATE)

    if ike_policy_report_list:
        IKE_POLICY_TEMPLATE[IKE_POLICIES_KEY][RESOURCES_KEY] = ike_policy_report_list
        validation_dict.update(IKE_POLICY_TEMPLATE)
        provisioning_dict.update(IKE_POLICY_TEMPLATE)

    if ipsec_policy_report_list:
        IPSEC_POLICY_TEMPLATE[IPSEC_POLICIES_KEY][RESOURCES_KEY] = ipsec_policy_report_list
        validation_dict.update(IPSEC_POLICY_TEMPLATE)
        provisioning_dict.update(IPSEC_POLICY_TEMPLATE)

    if acl_report_list:
        ACL_TEMPLATE[ACL_KEY][RESOURCES_KEY] = acl_report_list
        validation_dict.update(ACL_TEMPLATE)
        provisioning_dict.update(ACL_TEMPLATE)

    if security_group_report_list:
        SECURITY_GROUP_TEMPLATE[SECURITY_GROUP_KEY][RESOURCES_KEY] = security_group_report_list
        provisioning_dict.update(SECURITY_GROUP_TEMPLATE)

    if public_gateway_report_list:
        PUBLIC_GATEWAY_TEMPLATE[PUBLIC_GATEWAY_KEY][RESOURCES_KEY] = public_gateway_report_list
        provisioning_dict.update(PUBLIC_GATEWAY_TEMPLATE)

    if address_prefix_report_list:
        ADDRESS_PREFIX_TEMPLATE[ADDRESS_PREFIX_KEY][RESOURCES_KEY] = address_prefix_report_list
        provisioning_dict.update(ADDRESS_PREFIX_TEMPLATE)

    if subnet_report_list:
        SUBNET_TEMPLATE[SUBNET_KEY][RESOURCES_KEY] = subnet_report_list
        provisioning_dict.update(SUBNET_TEMPLATE)

    if route_report_list:
        ROUTE_TEMPLATE[ROUTE_KEY][RESOURCES_KEY] = route_report_list
        provisioning_dict.update(ROUTE_TEMPLATE)

    if attach_pg_to_subnet_report_list:
        ATTACH_PG_TO_SUBNET_TEMPLATE[ATTACH_PG_TO_SUBNET_KEY][RESOURCES_KEY] = attach_pg_to_subnet_report_list
        provisioning_dict.update(ATTACH_PG_TO_SUBNET_TEMPLATE)

    if instance_report_list:
        INSTANCE_TEMPLATE[INSTANCE_KEY][RESOURCES_KEY] = instance_report_list
        provisioning_dict.update(INSTANCE_TEMPLATE)

    if floating_ip_report_list:
        FLOATING_IP_TEMPLATE[FLOATING_IP_KEY][RESOURCES_KEY] = floating_ip_report_list
        provisioning_dict.update(FLOATING_IP_TEMPLATE)

    if instance_profile_report_list:
        INSTANCE_PROFILE_TEMPLATE[INSTANCE_PROFILE_KEY][RESOURCES_KEY] = instance_profile_report_list
        validation_dict.update(INSTANCE_PROFILE_TEMPLATE)

    if image_report_list:
        IMAGE_TEMPLATE[IMAGE_KEY][RESOURCES_KEY] = image_report_list
        validation_dict.update(IMAGE_TEMPLATE)

    if volume_report_list:
        VOLUME_TEMPLATE[VOLUME_KEY][RESOURCES_KEY] = volume_report_list
        validation_dict.update(VOLUME_TEMPLATE)

    if vpn_report_list:
        VPN_TEMPLATE[VPN_KEY][RESOURCES_KEY] = vpn_report_list
        provisioning_dict.update(VPN_TEMPLATE)

    if vpn_connections_report_list:
        VPN_CONNECTION_TEMPLATE[VPN_CONNECTION_KEY][RESOURCES_KEY] = vpn_connections_report_list
        provisioning_dict.update(VPN_CONNECTION_TEMPLATE)

    if adding_local_cidr_report_list:
        ADDING_LOCAL_CIDR_TEMPLATE[ADDING_LOCAL_CIDR_KEY][RESOURCES_KEY] = adding_local_cidr_report_list
        provisioning_dict.update(ADDING_LOCAL_CIDR_TEMPLATE)

    if adding_peer_cidr_report_list:
        ADDING_PEER_CIDR_TEMPLATE[ADDING_PEER_CIDR_KEY][RESOURCES_KEY] = adding_peer_cidr_report_list
        provisioning_dict.update(ADDING_PEER_CIDR_TEMPLATE)

    if deleting_local_cidr_report_list:
        DELETING_LOCAL_CIDR_TEMPLATE[DELETING_LOCAL_CIDR_KEY][RESOURCES_KEY] = deleting_local_cidr_report_list
        provisioning_dict.update(DELETING_LOCAL_CIDR_TEMPLATE)

    if deleting_peer_cidr_report_list:
        DELETING_PEER_CIDR_TEMPLATE[DELETING_PEER_CIDR_KEY][RESOURCES_KEY] = deleting_peer_cidr_report_list
        provisioning_dict.update(DELETING_PEER_CIDR_TEMPLATE)

    if kubernetes_cluster_report_list:
        KUBERNETES_CLUSTER_REPORT_TEMPLATE[KUBERNETES_KEY][RESOURCES_KEY] = kubernetes_cluster_report_list
        provisioning_dict.update(KUBERNETES_CLUSTER_REPORT_TEMPLATE)

    if load_balancer_report_list:
        LOAD_BALANCER_TEMPLATE[LOAD_BALANCER_KEY][RESOURCES_KEY] = load_balancer_report_list
        provisioning_dict.update(LOAD_BALANCER_TEMPLATE)

    if validation_tasks:
        workflow_steps.append(
            chord(group(validation_tasks), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Validation Tasks Chord Finisher")))

    if not vpc.status == CREATED:
        workflow_steps.append(
            chord(group([task_configure_ibm_vpc.si(
                task_id=task_id, region=region, cloud_id=cloud_id, vpc_id=vpc_id)]),
                update_group_tasks.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                      message="VPC Creation Task Chord Finisher")))

    if regional_tasks:
        workflow_steps.append(
            chord(group(regional_tasks), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Pre-requisite Tasks Chord Finisher")))

    if vpc_tasks:
        workflow_steps.append(
            chord(group(vpc_tasks), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="VPC Tasks Chord Finisher")))

    if subnet_tasks_list:
        workflow_steps.append(
            chord(group(subnet_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Subnet Tasks Chord Finisher")))

    if route_tasks_list:
        workflow_steps.append(
            chord(group(route_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Route Tasks Chord Finisher")))

    if instance_vpns_tasks_list:
        workflow_steps.append(
            chord(group(instance_vpns_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Instance VPNs Task Chord Finisher")))

    if kubernetes_cluster_task_list:
        workflow_steps.append(
            chord(group(kubernetes_cluster_task_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="IKS Task Chord Finisher")))

    if load_balancer_tasks_list or vpn_connections_task_list:
        workflow_steps.append(
            chord(group(load_balancer_tasks_list + vpn_connections_task_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="LoadBalancer Task Chord Finisher")))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))

    if vpc.status == CREATED and len(validation_dict) == 2:
        validation_status = SUCCESS

    if vpc.status == CREATED and len(provisioning_dict) == 1:
        provisioning_status = SUCCESS
        LOGGER.error("Nothing has been added for provisioning")

    if provisioning_status == SUCCESS and validation_status == SUCCESS:
        report_status = SUCCESS

    provisioning = {"status": provisioning_status, "message": "", "steps": provisioning_dict}
    validation = {"status": validation_status, "message": "", "steps": validation_dict}
    report = {"status": report_status, "message": "", "steps": {"provisioning": provisioning, "validation": validation}}
    self.ibm_task.report = report
    doosradb.session.commit()

    if vpc.workspace:
        vpc.workspace.request_metadata = request_metadata
        doosradb.session.commit()

    chain(workflow_steps).delay()
    LOGGER.info("IBM VPC workflow for task with ID: '{id}' created successfully".format(id=task_id))


@celery.task(name="delete_ibm_vpc_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpc_workflow(self, task_id, cloud_id, region, vpc_id):
    """
    This request deletes a VPC and its attached resources,
    such as subnets and its resources such as vpn gateways
    and the instances and its floating ip and then the public gateways
    @param ibm_vpc:
    @return:
    """
    workflow_steps, public_gateway_task_lists, floating_ip_tasks_list = list(), list(), list()
    load_balancer_task_list, vpn_instance_tasks_list, subnet_tasks_list, route_tasks_list, kubernetes_tasks_list = \
        list(), list(), list(), list(), list()
    ibm_vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    if not ibm_vpc:
        return

    for iks in ibm_vpc.kubernetes_clusters.all():
        kubernetes_tasks_list.append(task_delete_ibm_k8s_cluster.si(
            task_id=task_id, cloud_id=cloud_id, region=region, k8s_cluster_id=iks.id))

    for lb in ibm_vpc.load_balancers.all():
        load_balancer_task_list.append(task_delete_ibm_load_balancer.si(
            task_id=task_id, cloud_id=cloud_id, region=region, load_balancer_id=lb.id))

    for vpn in ibm_vpc.vpn_gateways.all():
        vpn_instance_tasks_list.append(task_delete_ibm_vpn_gateway.si(
            task_id=task_id, cloud_id=cloud_id, region=region, vpn_id=vpn.id))

    for instance in ibm_vpc.instances.all():
        for network_interface in instance.network_interfaces.all():
            if network_interface.floating_ip:
                floating_ip_tasks_list.append(
                    task_delete_ibm_floating_ip.si(task_id=task_id, cloud_id=cloud_id, region=region,
                                                   floating_ip_id=network_interface.floating_ip.id))

        vpn_instance_tasks_list.append(task_delete_ibm_instance.si(
            task_id=task_id, cloud_id=cloud_id, region=region, instance_id=instance.id))

    for subnet in ibm_vpc.subnets.all():
        subnet_tasks_list.append(task_delete_ibm_subnet.si(
            task_id=task_id, cloud_id=cloud_id, region=region, subnet_id=subnet.id))

    for route in ibm_vpc.vpc_routes.all():
        route_tasks_list.append(task_delete_ibm_vpc_route.si(
            task_id=task_id, cloud_id=cloud_id, region=region, subnet_id=route.id))

    for public_gateway in ibm_vpc.public_gateways.all():
        public_gateway_task_lists.append(task_delete_public_gateway.si(
            task_id=task_id, cloud_id=cloud_id, region=region, public_gateway_id=public_gateway.id))

    if load_balancer_task_list and len(load_balancer_task_list) == 1:
        workflow_steps.extend(load_balancer_task_list)
    elif load_balancer_task_list:
        workflow_steps.append(
            chord(group(load_balancer_task_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Load Balancers Tasks Chord Finisher")))

    if floating_ip_tasks_list and len(floating_ip_tasks_list) == 1:
        workflow_steps.extend(floating_ip_tasks_list)
    elif floating_ip_tasks_list:
        workflow_steps.append(
            chord(group(floating_ip_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Floating IP's Tasks Chord Finisher")))

    if kubernetes_tasks_list and len(kubernetes_tasks_list) == 1:
        workflow_steps.extend(kubernetes_tasks_list)
    elif kubernetes_tasks_list:
        workflow_steps.append(
            chord(group(kubernetes_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Kubernetes Cluster Tasks Chord Finisher")))

    if vpn_instance_tasks_list and len(vpn_instance_tasks_list) == 1:
        workflow_steps.extend(vpn_instance_tasks_list)
    elif vpn_instance_tasks_list:
        workflow_steps.append(
            chord(group(vpn_instance_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="VPN/VSI's Tasks Chord Finisher")))

    if subnet_tasks_list and len(subnet_tasks_list) == 1:
        workflow_steps.extend(subnet_tasks_list)
    elif subnet_tasks_list:
        workflow_steps.append(
            chord(group(subnet_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Subnet Tasks Chord Finisher")))

    if public_gateway_task_lists and len(public_gateway_task_lists) == 1:
        workflow_steps.extend(public_gateway_task_lists)
    elif public_gateway_task_lists:
        workflow_steps.append(
            chord(group(public_gateway_task_lists), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Pbgws Tasks Chord Finisher")))

    workflow_steps.append(task_delete_ibm_vpc.si(task_id=task_id, cloud_id=cloud_id, region=region, vpc_id=vpc_id))
    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_delete_ibm_vpc_route", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpc_route(self, task_id, cloud_id, region, vpc_route_id):
    """
    This request deletes a VPC route
    @return:
    """
    ibm_vpc_route = doosradb.session.query(IBMVpcRoute).filter_by(id=vpc_route_id).first()
    if not ibm_vpc_route:
        return

    self.resource = ibm_vpc_route
    ibm_vpc_route.status = DELETING
    doosradb.session.commit()

    if ibm_vpc_route.resource_id:
        if self.ibm_manager.rias_ops.fetch_ops.get_vpc_route(ibm_vpc_route.resource_id):
            self.ibm_manager.rias_ops.delete_vpc_route(ibm_vpc_route)

    ibm_vpc_route.status = DELETED
    doosradb.session.delete(ibm_vpc_route)
    doosradb.session.commit()
    LOGGER.info("VPC route '{name}' deleted successfully on IBM Cloud".format(name=ibm_vpc_route.name))


@celery.task(name="task_delete_ibm_vpc_route_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpc_route_workflow(self, task_id, cloud_id, region, vpc_route_id):
    """
    This request is workflow for deletion of vpc routes
    @return:
    """

    workflow_steps = list()

    ibm_vpc_route = doosradb.session.query(IBMVpcRoute).filter_by(id=vpc_route_id).first()
    if not ibm_vpc_route:
        return

    workflow_steps.append(task_delete_ibm_vpc_route.si(task_id=task_id, cloud_id=cloud_id,
                                                       region=region, vpc_route_id=vpc_route_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()
