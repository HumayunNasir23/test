import uuid
import random

from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATION_PENDING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.instances.consts import NETWORK_INTERFACE_NAME, VOLUME_ATTACHMENT_NAME, VOLUME_NAME
from doosra.ibm.managers.exceptions import (
    IBMAuthError,
    IBMConnectError,
    IBMExecuteError,
    IBMInvalidRequestError,
)
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMVpcNetwork, KubernetesCluster
from doosra.models.ibm.instance_models import IBMInstance, IBMInstanceProfile, IBMImage, IBMNetworkInterface, \
    IBMOperatingSystem, IBMVolumeProfile, IBMVolume, IBMVolumeAttachment
from doosra.models.ibm.load_balancer_models import IBMPool, IBMListener, IBMLoadBalancer, IBMPoolMember, IBMHealthCheck
from doosra.models.ibm.resource_group_models import IBMResourceGroup
from doosra.models.ibm.ssh_key_models import IBMSshKey
from doosra.models.ibm.subnet_models import IBMSubnet
from doosra.models.ibm.vpns_models import IBMIKEPolicy, IBMIPSecPolicy, IBMVpnGateway, IBMVpnConnection


def get_ibm_regions(ibm_cloud):
    """
    Get a list of available IBM regions
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud)
        regions_list = ibm_manager.rias_ops.fetch_ops.get_regions()
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return regions_list


def get_ibm_zones(ibm_cloud, region):
    """
    Get a list of available IBM zones against an IBM region
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud, region)
        zones_list = ibm_manager.rias_ops.fetch_ops.get_zones()
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return zones_list


def get_ibm_resource_groups(ibm_cloud):
    """
    Get a list of available IBM resource groups for an IBM cloud account
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud)
        resource_groups = ibm_manager.resource_ops.fetch_ops.get_resource_groups()
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return resource_groups


def get_ibm_address_prefixes(vpc):
    """
    Get a list of available address prefixes for an IBM VPC network
    :return:
    """
    address_prefixes = list()
    try:
        if vpc.resource_id:
            ibm_manager = IBMManager(vpc.ibm_cloud, vpc.region)
            address_prefixes = ibm_manager.rias_ops.fetch_ops.get_all_vpc_address_prefixes(
                vpc.resource_id
            )
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            vpc.ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return address_prefixes


def get_ibm_instance_profiles(ibm_cloud, region):
    """
    This request lists all instance profiles available in the region
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud, region)
        instance_profiles_list = (
            ibm_manager.rias_ops.fetch_ops.get_all_instance_profiles()
        )
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return instance_profiles_list


def get_ibm_images(ibm_cloud, region):
    """
    This request lists all images available in the region
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud, region)
        images_list = ibm_manager.rias_ops.fetch_ops.get_all_images(status="available")
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return images_list


def get_ibm_operating_systems(ibm_cloud, region):
    """
    This request lists all operating_system available in the region
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud, region)
        operating_systems_list = (
            ibm_manager.rias_ops.fetch_ops.get_all_operating_systems()
        )
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return operating_systems_list


def get_ibm_volume_profiles(ibm_cloud, region):
    """
    This request lists all volume profiles available in the region
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud, region)
        volume_profiles_list = ibm_manager.rias_ops.fetch_ops.get_all_volume_profiles()
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return volume_profiles_list


def get_cos_buckets(ibm_cloud, region, get_objects, primary_objects=True):
    """
    This request lists all COS buckets available in the region
    :return:
    """
    try:
        if not ibm_cloud.service_credentials:
            raise IBMInvalidRequestError("IBM Service Credential for COS is required")

        ibm_manager = IBMManager(ibm_cloud, region)
        buckets = ibm_manager.cos_ops.fetch_ops.get_buckets(get_objects=get_objects, primary_objects=primary_objects)

    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
        return None, False
    else:
        return buckets, True


def configure_and_save_obj_confs(ibm_manager, obj):
    """
    This method pushes the config objects on IBM, and validates these objects.
    :return:
    """
    if not ibm_manager:
        return

    ibm_manager.rias_ops.push_obj_confs(obj)
    existing_obj = ibm_manager.rias_ops.fetch_ops.list_obj_method_mapper(obj)
    if not existing_obj:
        raise IBMInvalidRequestError(
            "Failed to configure '{obj}' with name '{name}'".format(
                obj=obj.__class__.__name__, name=obj.name
            )
        )

    return existing_obj[0]


def construct_ibm_vpc_workspace_json(ibm_vpc_network, request_metadata):
    """
    Construct VPC workflow response json to be used by client side to keep track of unprovisioned/provisioned resources
    :return:
    """
    from doosra.models import IBMDedicatedHost

    used_dh_name_instance_ids_dict = dict()

    sg_name = [sg["name"] for sg in ibm_vpc_network["security_groups"]]
    for security_group in request_metadata.get("security_groups", []):
        if security_group["name"] in sg_name:
            continue
        security_group.update({"id": str(uuid.uuid4().hex)})
        security_group.update({"status": CREATION_PENDING})
        ibm_vpc_network["security_groups"].append(security_group)

    sec_groups_dict = {security_group["name"]: security_group["id"] for security_group in
                       ibm_vpc_network["security_groups"]}

    vpn_name = [vpn["name"] for vpn in ibm_vpc_network["vpn_gateways"]]
    for vpn in request_metadata.get("vpn_gateways", []):
        # TODO  try to get data from ibm_Vpc_network
        if vpn["name"] in vpn_name:
            continue
        subnet = doosradb.session.query(IBMSubnet).filter_by(name=vpn["subnet"],
                                                             vpc_id=ibm_vpc_network["id"],
                                                             region=ibm_vpc_network["region"],
                                                             cloud_id=ibm_vpc_network["cloud"]).first()
        ike_policy_list = []
        ipsec_policy_list = []
        for connection in vpn["connections"]:
            if connection.get("ike_policy"):
                ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(name=connection["ike_policy"],
                                                                            region=ibm_vpc_network["region"],
                                                                            cloud_id=ibm_vpc_network["cloud"]
                                                                            ).first()
                if ike_policy:
                    ike_policy_list.append(ike_policy)

            if connection.get("ipsec_policy"):
                ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(name=connection["ipsec_policy"],
                                                                                region=ibm_vpc_network["region"],
                                                                                cloud_id=ibm_vpc_network["cloud"]
                                                                                ).first()
                if ipsec_policy:
                    ipsec_policy_list.append(ipsec_policy)

        vpn_payload = {
            IBMVpnGateway.ID_KEY: str(uuid.uuid4().hex),
            IBMVpnGateway.NAME_KEY: vpn["name"],
            IBMVpnGateway.REGION_KEY: ibm_vpc_network["region"],
            IBMVpnGateway.SUBNET_KEY: subnet.to_json() if subnet else [],
            IBMVpnGateway.CREATED_AT_KEY: "",
            IBMVpnGateway.RESOURCE_GROUP_KEY: {IBMResourceGroup.ID_KEY: ibm_vpc_network["resource_group"]["id"],
                                               IBMResourceGroup.NAME_KEY: ibm_vpc_network["resource_group"]["name"]},
            IBMVpnGateway.VPC_KEY: {
                "id": ibm_vpc_network["id"],
                "name": ibm_vpc_network["name"]
            },
            IBMVpnGateway.IP_ADDRESS_KEY: "",
            IBMVpnGateway.GATEWAY_STATUS_KEY: "",
            IBMVpnGateway.STATUS_KEY: CREATION_PENDING,
            IBMVpnGateway.LOCATION_KEY: "",
            IBMVpnGateway.CONNECTIONS_KEY: [{
                IBMVpnConnection.ID_KEY: str(uuid.uuid4().hex),
                IBMVpnConnection.NAME_KEY: connection.get("name"),
                IBMVpnConnection.GATEWAY_ADDRESS_KEY: "",
                IBMVpnConnection.PEER_ADDRESS_KEY: connection.get("peer_address"),
                IBMVpnConnection.LOCAL_CIDRS_KEY: connection.get("local_cidrs") or [],
                IBMVpnConnection.PEER_CIDRS_KEY: connection.get("peer_cidrs") or [],
                IBMVpnConnection.PSK_KEY: connection.get("pre_shared_secret"),
                IBMVpnConnection.VPN_STATUS_KEY: "",
                IBMVpnConnection.ROUTE_MODE_KEY: "",
                IBMVpnConnection.CREATED_AT_KEY: "",
                IBMVpnConnection.ADMIN_STATE_UP_KEY: "",
                IBMVpnConnection.DEAD_PEER_DETECTION_KEY: {
                    IBMVpnConnection.DPD_ACTION_KEY: connection["dead_peer_detection"].get("action"),
                    IBMVpnConnection.DPD_INTERVAL_KEY: connection["dead_peer_detection"].get("interval"),
                    IBMVpnConnection.DPD_TIMEOUT_KEY: connection["dead_peer_detection"].get("timeout"),
                } if connection.get("dead_peer_detection") else "",
                IBMVpnConnection.IKE_POLICY: [ike_policy.to_json() for ike_policy in ike_policy_list if
                                              ike_policy.name == connection.get("ike_policy")
                                              ][0] if ike_policy_list else {},
                IBMVpnConnection.IPSEC_POLICY: [ipsec_policy.to_json() for ipsec_policy in ipsec_policy_list if
                                                ipsec_policy.name == connection.get("ipsec_policy")
                                                ][0] if ipsec_policy_list else {},
                IBMVpnConnection.DISCOVERED_LOCAL_CIDRS: connection.get("discovered_local_cidrs", []),
            } for connection in vpn["connections"]],

            IBMVpnGateway.CLOUD_ID_KEY: ibm_vpc_network["cloud"]
        }

        ibm_vpc_network["vpn_gateways"].append(vpn_payload)

    instances_name = [instance["name"] for instance in ibm_vpc_network["instances"]]
    for instance in request_metadata.get("instances", []):
        if instance["name"] in instances_name:
            continue
        subnets = []
        for network_interface in instance["network_interfaces"]:
            subnet = doosradb.session.query(IBMSubnet).filter_by(name=network_interface["subnet"],
                                                                 region=ibm_vpc_network["region"],
                                                                 cloud_id=ibm_vpc_network["cloud"],
                                                                 vpc_id=ibm_vpc_network["id"]).first()
            if subnet:
                subnets.append(subnet)

        ssh_keys = []
        for ssh_key in instance.get("ssh_keys", []):
            ssh_key = doosradb.session.query(IBMSshKey).filter_by(name=ssh_key["name"],
                                                                  region=ibm_vpc_network["region"],
                                                                  cloud_id=ibm_vpc_network["cloud"]).first()
            if ssh_key:
                ssh_keys.append(ssh_key)

        dedicated_host_id = instance.get("dedicated_host_id")

        id = str(uuid.uuid4().hex)
        set_inst_payload = {
            IBMInstance.ID_KEY: id,
            IBMInstance.NAME_KEY: instance["name"],
            IBMInstance.REGION_KEY: ibm_vpc_network["region"],
            IBMInstance.ZONE_KEY: instance["zone"],
            IBMInstance.STATUS_KEY: CREATION_PENDING,
            IBMInstance.INSTANCE_STATUS_KEY: "",
            "dedicated_host_id": dedicated_host_id,
            "dedicated_host_name": instance.get("dedicated_host_name"),
            "dedicated_host_group_id": instance.get("dedicated_host_group_id"),
            "dedicated_host_group_name": instance.get("dedicated_host_group_name"),
            IBMInstance.IMAGE_KEY:
                {
                    IBMImage.ID_KEY: str(uuid.uuid4().hex),
                    IBMImage.NAME_KEY: instance["extras"].get(
                        "public_image") or instance["extras"].get("custom_image") or instance["name"],
                    IBMImage.IMAGE_TEMPLATE_PATH_KEY: instance["image"].get("image_template_path"),
                    IBMImage.REGION_KEY: ibm_vpc_network["region"],
                    IBMImage.VISIBILITY_KEY: instance["extras"]["image"].get("visibility"),
                    IBMImage.STATUS_KEY: instance["image"].get("status"),
                    IBMImage.SIZE_KEY: instance["extras"]["image"].get("size"),
                    IBMImage.CLASSICAL_IMAGE_NAME: instance["extras"]["image"].get("classical_image_name"),
                    IBMImage.OPERATING_SYSTEM_KEY:
                        {
                            IBMOperatingSystem.ID_KEY: str(uuid.uuid4().hex),
                            IBMOperatingSystem.NAME_KEY: instance["image"].get("operating_system_name"),
                            IBMOperatingSystem.ARCHITECTURE_KEY: instance["extras"]["image"]["operating_systems"].get(
                                "architecture") if instance["extras"]["image"].get("operating_systems") else "",
                            IBMOperatingSystem.FAMILY_KEY: instance["extras"]["image"]["operating_systems"].get(
                                "family") if instance["extras"]["image"].get("operating_systems") else "",
                            IBMOperatingSystem.VENDOR_KEY: instance["extras"]["image"]["operating_systems"].get(
                                "vendor") if instance["extras"]["image"].get("operating_systems") else "",
                            IBMOperatingSystem.VERSION_KEY: instance["extras"]["image"]["operating_systems"].get(
                                "version") if instance["extras"]["image"].get("operating_systems") else ""
                        },
                    IBMImage.CLOUD_ID_KEY: ibm_vpc_network["cloud"]
                },
            IBMInstance.INSTANCE_PROFILE_KEY:
                {
                    IBMInstanceProfile.ID_KEY: str(uuid.uuid4().hex),
                    IBMInstanceProfile.NAME_KEY: instance["extras"]["instance_profile"].get("name"),
                    IBMInstanceProfile.FAMILY_KEY: instance["extras"]["instance_profile"].get("family"),
                    IBMInstanceProfile.ARCHITECTURE_KEY: instance["extras"]["instance_profile"].get("architecture"),
                },
            IBMInstance.SSH_KEY: [ssh_key.to_json() for ssh_key in ssh_keys] if ssh_keys else None,
            IBMInstance.NETWORK_INTERFACE_KEY:
                [
                    {
                        IBMNetworkInterface.ID_KEY: str(uuid.uuid4().hex),
                        IBMNetworkInterface.NAME_KEY: interface.get("name") or NETWORK_INTERFACE_NAME.format(random.randint(1, 999), index),
                        IBMNetworkInterface.SUBNET_KEY: [subnet.to_json() for subnet in subnets
                                                         if subnet.name == interface.get("subnet")][
                            0] if subnets else {},
                        IBMNetworkInterface.SECURITY_GROUP_KEY: [sec_groups_dict.get(name) for name in
                                                                 interface.get("security_groups", []) if
                                                                 sec_groups_dict.get(name)],
                        IBMNetworkInterface.INSTANCE_KEY: id,
                        "reserve_floating_ip": interface.get("reserve_floating_ip"),
                        "is_primary": interface.get("is_primary", False)
                    } for index, interface in enumerate(instance.get("network_interfaces", []))
                ],
            IBMInstance.USER_DATA_KEY: instance.get("user_data"),
            IBMInstance.STATE_KEY: instance.get("state"),
            IBMInstance.BOOT_VOLUME_ATTACHMENT_KEY: {
                IBMVolumeAttachment.ID_KEY: str(uuid.uuid4().hex),
                IBMVolumeAttachment.NAME_KEY: VOLUME_ATTACHMENT_NAME.format(instance["name"]),
                IBMVolumeAttachment.TYPE: "boot",
                IBMVolumeAttachment.IS_DELETE_KEY: True,
                IBMVolumeAttachment.VOLUME_KEY: {
                    IBMVolume.ID_KEY: str(uuid.uuid4().hex),
                    IBMVolume.NAME_KEY: VOLUME_NAME.format(instance["name"]),
                    IBMVolume.CAPACITY_KEY: 100,
                    IBMVolume.IOPS_KEY: "10iops-tier",
                    IBMVolume.ZONE_KEY: instance.get("zone"),
                    IBMVolume.ENCRYPTION_KEY: "provider_managed",
                    IBMVolume.PROFILE_KEY: {
                        IBMVolumeProfile.ID_KEY: str(uuid.uuid4().hex),
                        IBMVolumeProfile.NAME_KEY: "10iops-tier",
                        IBMVolumeProfile.FAMILY_KEY: "tiered",
                        IBMVolumeProfile.REGION_KEY: ibm_vpc_network["region"],
                        IBMVolumeProfile.GENERATION_KEY: None,
                    },
                    IBMVolume.STATUS_KEY: CREATION_PENDING,
                },
                IBMVolumeAttachment.IS_MIGRATION_ENABLED_KEY: False,
                IBMVolumeAttachment.VOLUME_INDEX_KEY: None
            },
            IBMInstance.VOLUME_ATTACHMENT_KEY:
                [
                    {
                        IBMVolumeAttachment.ID_KEY: str(uuid.uuid4().hex),
                        IBMVolumeAttachment.NAME_KEY: attachment.get("name"),
                        IBMVolumeAttachment.TYPE: attachment.get("type"),
                        IBMVolumeAttachment.IS_DELETE_KEY: attachment.get("is_delete"),
                        IBMVolumeAttachment.VOLUME_KEY: {
                            IBMVolume.ID_KEY: str(uuid.uuid4().hex),
                            IBMVolume.NAME_KEY: attachment["volume"].get("name"),
                            IBMVolume.CAPACITY_KEY: attachment["volume"].get("capacity"),
                            IBMVolume.IOPS_KEY: attachment["volume"].get("iops"),
                            IBMVolume.ZONE_KEY: attachment["volume"].get("zone"),
                            IBMVolume.ENCRYPTION_KEY: attachment["volume"].get("encryption"),
                            IBMVolume.ORIGINAL_CAPACITY_KEY: attachment["volume"].get("original_capacity"),
                            IBMVolume.PROFILE_KEY: {
                                IBMVolumeProfile.ID_KEY: str(uuid.uuid4().hex),
                                IBMVolumeProfile.NAME_KEY: attachment["volume"]["profile"].get("name"),
                                IBMVolumeProfile.FAMILY_KEY: attachment["volume"]["profile"].get("family"),
                                IBMVolumeProfile.REGION_KEY: attachment["volume"]["profile"].get("region"),
                                IBMVolumeProfile.GENERATION_KEY: attachment["volume"]["profile"].get("generation"),
                            },
                            IBMVolume.STATUS_KEY: attachment["volume"].get("status"),
                        },
                        IBMVolumeAttachment.IS_MIGRATION_ENABLED_KEY: attachment.get("is_migration_enabled"),
                        IBMVolumeAttachment.VOLUME_INDEX_KEY: attachment.get("volume_index")
                    } for attachment in instance.get("volume_attachments") or []

                ],
            IBMInstance.CLOUD_ID_KEY: ibm_vpc_network["cloud"],
            IBMInstance.VPC_KEY:
                {
                    IBMVpcNetwork.ID_KEY: ibm_vpc_network["id"],
                    IBMVpcNetwork.NAME_KEY: ibm_vpc_network["name"]
                },
            IBMInstance.IS_VOLUME_MIGRATION: instance.get("data_migration"),
            IBMInstance.ORIGINAL_IMAGE_KEY: instance.get("original_image"),
            IBMInstance.ORIGINAL_OPERATING_SYSTEM_NAME_KEY: instance.get("original_operating_system_name"),
            IBMInstance.MIG_INFO_KEY: {
                "bucket_name": instance["extras"].get("bucket_name"),
                "vpc_image_name": instance["extras"].get("vpc_image_name") or instance["image"].get("public_image") or instance.get("original_image"),
                "classical_account_id": instance["extras"].get("classical_account_id"),
                "classical_instance_id": instance["extras"].get("classical_instance_id"),
                "public_image": instance["extras"].get("public_image"),
                "custom_image": instance["extras"].get("custom_image"),
                "classical_image_id": instance["extras"].get("classical_image_id"),
                "bucket_object": instance["extras"].get("bucket_object"),
                "image_location": instance["extras"].get("image_location"),
                "image_type": instance["extras"].get("image_type"),
                "migration": instance["extras"].get("migration")
            },
            IBMInstance.INSTANCE_TYPE_KEY: instance.get("instance_type"),
            IBMInstance.DATA_CENTER_KEY: instance.get("data_center"),
            IBMInstance.AUTO_SCALE_GROUP_KEY: instance.get("auto_scale_group") or "",
            IBMInstance.NETWORK_ATTACHED_STORAGES_KEY: instance.get("network_attached_storages") or [],
        }
        if instance.get("nas_migration_info"):
            set_inst_payload["nas_migration_info"] = instance["nas_migration_info"]
        if instance.get("nas_meta_data"):
            set_inst_payload["nas_meta_data"] = instance["nas_meta_data"]

        for pool in set_inst_payload[IBMInstance.NETWORK_INTERFACE_KEY]:
            if pool["is_primary"]:
                set_inst_payload[IBMInstance.PRIMARY_NETWORK_INTERFACE_KEY] = pool

        dh_name = instance.get("dedicated_host_name")
        if dh_name:
            if dh_name not in used_dh_name_instance_ids_dict:
                used_dh_name_instance_ids_dict[dh_name] = []

            used_dh_name_instance_ids_dict[dh_name].append(set_inst_payload["id"])

        ibm_vpc_network["instances"].append(set_inst_payload)

    lb_name = [lb["name"] for lb in ibm_vpc_network["load_balancers"]]
    for load_balancer in request_metadata.get("load_balancers", []):
        if load_balancer["name"] in lb_name:
            continue
        subnets = []
        for subnet_name in load_balancer[IBMLoadBalancer.SUBNETS_KEY]:
            subnet = doosradb.session.query(IBMSubnet).filter_by(name=subnet_name,
                                                                 region=ibm_vpc_network["region"],
                                                                 cloud_id=ibm_vpc_network["cloud"],
                                                                 vpc_id=ibm_vpc_network["id"]).first()
            if subnet:
                subnets.append(subnet)

        set_load_balancer_payload = {
            IBMLoadBalancer.ID_KEY: str(uuid.uuid4().hex),
            IBMLoadBalancer.NAME_KEY: load_balancer.get(IBMLoadBalancer.NAME_KEY),
            IBMLoadBalancer.PUBLIC_KEY: load_balancer.get(IBMLoadBalancer.PUBLIC_KEY),
            IBMLoadBalancer.REGION_KEY: ibm_vpc_network.get(IBMVpcNetwork.REGION_KEY),
            IBMLoadBalancer.STATUS_KEY: CREATION_PENDING,
            IBMLoadBalancer.PROVISIONING_STATUS_KEY: None,
            IBMLoadBalancer.HOST_NAME_KEY: load_balancer.get(IBMLoadBalancer.HOST_NAME_KEY),
            IBMLoadBalancer.PRIVATE_IPS_KEY: load_balancer.get(IBMLoadBalancer.PRIVATE_IPS_KEY),
            IBMLoadBalancer.PUBLIC_IPS_KEY: load_balancer.get(IBMLoadBalancer.PUBLIC_IPS_KEY),
            IBMLoadBalancer.RESOURCE_GROUP_KEY: {IBMResourceGroup.ID_KEY: ibm_vpc_network["resource_group"]["id"],
                                                 IBMResourceGroup.NAME_KEY: ibm_vpc_network["resource_group"]["name"]},
            IBMLoadBalancer.CLOUD_ID_KEY: ibm_vpc_network[IBMVpcNetwork.CLOUD_ID_KEY],
            IBMLoadBalancer.VPC_KEY: {
                IBMLoadBalancer.ID_KEY: ibm_vpc_network[IBMVpcNetwork.ID_KEY],
                IBMLoadBalancer.NAME_KEY: ibm_vpc_network[IBMVpcNetwork.NAME_KEY],
            },
            IBMLoadBalancer.LISTENERS_KEY: [
                {
                    IBMListener.ID_KEY: str(uuid.uuid4().hex),
                    IBMListener.STATUS_KEY: CREATION_PENDING,
                    IBMListener.PORT_KEY: listener.get(IBMListener.PORT_KEY),
                    IBMListener.PROTOCOL_KEY: listener.get(IBMListener.PROTOCOL_KEY),
                    IBMListener.CERTIFICATE_INSTANCE: listener.get(IBMListener.CERTIFICATE_INSTANCE),
                    IBMListener.CONNECTION_LIMIT: listener.get(IBMListener.CONNECTION_LIMIT),
                    IBMListener.DEFAULT_POOL_KEY: listener.get(IBMListener.DEFAULT_POOL_KEY),
                    "is_default": listener.get("default_pool")

                } for listener in load_balancer.get(IBMLoadBalancer.LISTENERS_KEY) or []
            ],
            IBMLoadBalancer.SUBNETS_KEY: [subnet.to_json() for subnet in subnets if
                                          subnet.name in load_balancer.get("subnets")] if subnets else [],
            IBMLoadBalancer.POOLS_KEY: [
                {
                    IBMPool.ID_KEY: str(uuid.uuid4().hex),
                    IBMPool.STATUS_KEY: CREATION_PENDING,
                    IBMPool.NAME_KEY: pool.get(IBMPool.NAME_KEY),
                    IBMPool.PROTOCOL_KEY: pool.get(IBMPool.PROTOCOL_KEY),
                    IBMPool.SESSION_PERSISTENCE_KEY: pool.get(IBMPool.SESSION_PERSISTENCE_KEY),
                    IBMPool.ALGORITHM_KEY: pool.get(IBMPool.ALGORITHM_KEY),
                    IBMPool.HEALTH_CHECK_KEY: {
                        IBMHealthCheck.ID_KEY: str(uuid.uuid4().hex),
                        IBMHealthCheck.DELAY_KEY: pool["health_monitor"].get(IBMHealthCheck.DELAY_KEY),
                        IBMHealthCheck.MAX_RETRIES_KEY: pool["health_monitor"].get(IBMHealthCheck.MAX_RETRIES_KEY),
                        IBMHealthCheck.TIMEOUT_KEY: pool["health_monitor"].get(IBMHealthCheck.TIMEOUT_KEY),
                        IBMHealthCheck.TYPE_KEY: pool.get(IBMPool.PROTOCOL_KEY),
                        IBMHealthCheck.PORT_KEY: pool["health_monitor"].get(IBMHealthCheck.PORT_KEY),
                        IBMHealthCheck.URL_KEY: pool["health_monitor"].get(IBMHealthCheck.URL_KEY),
                    } if pool.get("health_monitor") else None,
                    IBMPool.POOL_MEMBER_KEY: [
                        {
                            IBMPoolMember.ID_KEY: str(uuid.uuid4().hex),
                            IBMPoolMember.PORT_KEY: pool_member.get(IBMPoolMember.PORT_KEY),
                            IBMPoolMember.INSTANCE_KEY:
                                next((instance for instance in ibm_vpc_network["instances"] if
                                      instance.get("name") == pool_member.get("instance")), None),
                            IBMPoolMember.INSTANCE_ID_KEY:
                                next((instance.get("id") for instance in ibm_vpc_network["instances"] if
                                      instance.get("name") == pool_member.get("instance")), None)
                        } for pool_member in pool.get("members") or []
                    ],
                } for pool in load_balancer.get(IBMLoadBalancer.POOLS_KEY, [])
            ]
        }

        for pool in set_load_balancer_payload[IBMLoadBalancer.POOLS_KEY]:
            for listener in set_load_balancer_payload[IBMLoadBalancer.LISTENERS_KEY]:
                if pool[IBMPool.NAME_KEY] == listener["is_default"]:
                    listener[IBMListener.DEFAULT_POOL_KEY] = pool["id"]

        ibm_vpc_network["load_balancers"].append(set_load_balancer_payload)

    ibm_vpc_network["kubernetes_clusters"] = []
    kubernetes_cluster_name = [kubernetes_cluster["name"] for kubernetes_cluster
                               in ibm_vpc_network["k8s_clusters"]]
    if kubernetes_cluster_name:
        kubernetes_cluster_name = kubernetes_cluster_name[0]
        kubernetes_cluster = doosradb.session.query(KubernetesCluster).filter_by(name=kubernetes_cluster_name).first()
        # TODO make managed view and DRAAS cluster keys generalized
        ibm_vpc_network.pop("k8s_clusters")
        ibm_vpc_network["kubernetes_clusters"].append(kubernetes_cluster.to_json())

    ibm_vpc_network["dedicated_hosts"] = []
    if "dedicated_hosts" in request_metadata:
        ibm_vpc_network["dedicated_hosts"] = request_metadata["dedicated_hosts"]

    for dedicated_host_name in used_dh_name_instance_ids_dict:
        found = False

        for dh_json in ibm_vpc_network["dedicated_hosts"]:
            if dh_json["name"] == dedicated_host_name:
                found = True
                dh_json["instances"] = used_dh_name_instance_ids_dict[dedicated_host_name]
                break

        if found:
            continue

        dedicated_host = \
            doosradb.session.query(IBMDedicatedHost).filter_by(
                cloud_id=ibm_vpc_network[IBMVpcNetwork.CLOUD_ID_KEY], name=dedicated_host_name,
                region=ibm_vpc_network["region"]
            ).first()
        if not dedicated_host:
            continue

        dedicated_host_json = dedicated_host.to_json()
        dedicated_host_json[IBMDedicatedHost.INSTANCES_KEY].extend(used_dh_name_instance_ids_dict[dedicated_host_name])

        ibm_vpc_network["dedicated_hosts"].append(dedicated_host_json)
    for provisioned_dh in request_metadata.get("provisioned_dedicated_host_ids", []):
        dedicated_host = doosradb.session.query(IBMDedicatedHost).filter_by(cloud_id=ibm_vpc_network["cloud"],
                                                                            id=provisioned_dh,
                                                                            region=ibm_vpc_network["region"]).first()
        if not dedicated_host:
            continue

        current_app.logger.info(dedicated_host.name)
        current_app.logger.info(used_dh_name_instance_ids_dict)
        if dedicated_host.name in list(used_dh_name_instance_ids_dict.keys()):
            continue

        ibm_vpc_network["dedicated_hosts"].append(dedicated_host.to_json())

    if not ibm_vpc_network["dedicated_hosts"]:
        for instance in ibm_vpc_network["instances"]:
            if instance[IBMInstance.STATUS_KEY] == CREATION_PENDING:
                instance["dedicated_host_id"] = None
                instance["dedicated_host_name"] = None

    else:
        for dh in ibm_vpc_network["dedicated_hosts"]:
            for instance_id in dh["instances"]:
                for instance in ibm_vpc_network["instances"]:
                    if instance["id"] == instance_id:
                        instance["dedicated_host_id"] = dh["id"]
                        break

    return ibm_vpc_network
