import logging

from doosra.models import *
from doosra import db as doosradb

LOGGER = logging.getLogger("billing_utils.py")

# Register resources required for billing in below dictionary
IBM_BILLING_RESOURCES_LIB = {
    IBMAddressPrefix.__name__: "ADDRESS-PREFIX",
    IBMImage.__name__: "IMAGE",
    IBMInstance.__name__: "INSTANCE",
    IBMInstanceProfile.__name__: "INSTANCE-PROFILE",
    IBMLoadBalancer.__name__: "LOAD-BALANCER",
    IBMNetworkAcl.__name__: "NETWORK-ACL",
    IBMNetworkAclRule.__name__: "NETWORK-ACL-RULE",
    IBMPublicGateway.__name__: "PUBLIC-GATEWAY",
    IBMResourceGroup.__name__: "RESOURCE-GROUP",
    IBMSecurityGroup.__name__: "SECURITY-GROUP",
    IBMSecurityGroupRule.__name__: "SECURITY-GROUP-RULE",
    IBMSubnet.__name__: "SUBNET",
    IBMVolumeProfile.__name__: "VOLUME-PROFILE",
    IBMVpcRoute.__name__: "VPC-ROUTE",
    IBMVpcNetwork.__name__: "VPC",
    IBMSshKey.__name__: "SSH-KEY",
    IBMVpnGateway.__name__: "VPN-GATEWAY",
    TransitGateway.__name__: "TRANSIT-GATEWAY",
    TransitGatewayConnection.__name__: "TRANSIT-GATEWAY-CONNECTION",
    IBMVolume.__name__: "VOLUME",
    IBMVolumeAttachment.__name__: "VOLUME-ATTACHMENT",
    IBMVpnConnection.__name__: "VPN-CONNECTION",
    IBMIKEPolicy.__name__: "IKE-POLICY",
    IBMFloatingIP.__name__: "FLOATING-IP",
    IBMIPSecPolicy.__name__: "IPSEC-POLICY",
    IBMOperatingSystem.__name__: "OPERATING-SYSTEM",
}

IBM_BILLING_RESOURCES_CLOUD_LIB = {
    IBMAddressPrefix.__name__: "resource.ibm_vpc_network.ibm_cloud",
    IBMImage.__name__: "resource.ibm_cloud",
    IBMInstance.__name__: "resource.ibm_cloud",
    IBMInstanceProfile.__name__: "resource.ibm_cloud",
    IBMLoadBalancer.__name__: "resource.ibm_cloud",
    IBMNetworkAcl.__name__: "resource.ibm_cloud",
    IBMNetworkAclRule.__name__: "resource.ibm_network_acl.ibm_cloud",
    IBMPublicGateway.__name__: "resource.ibm_cloud",
    IBMResourceGroup.__name__: "resource.ibm_cloud",
    IBMSecurityGroup.__name__: "resource.ibm_cloud",
    IBMSecurityGroupRule.__name__: "resource.security_group.ibm_cloud",
    IBMSubnet.__name__: "resource.ibm_cloud",
    IBMVolumeProfile.__name__: "resource.ibm_cloud",
    IBMVpcRoute.__name__: "resource.ibm_cloud",
    IBMVpcNetwork.__name__: "resource.ibm_cloud",
    IBMSshKey.__name__: "resource.ibm_cloud",
    IBMVpnGateway.__name__: "resource.ibm_cloud",
    TransitGateway.__name__: "resource.ibm_cloud",
    TransitGatewayConnection.__name__: "resource.transit_gateway.ibm_cloud",
    IBMVolume.__name__: "resource.ibm_cloud",
    IBMVolumeAttachment.__name__: "resource.volume.ibm_cloud",
    IBMVpnConnection.__name__: "resource.ibm_vpn_gateway.ibm_cloud",
    IBMIKEPolicy.__name__: "resource.ibm_cloud",
    IBMFloatingIP.__name__: "resource.ibm_cloud",
    IBMIPSecPolicy.__name__: "resource.ibm_cloud",
    IBMOperatingSystem.__name__: "resource.ibm_cloud",
}

CLOUD_TYPE_LIB = {
    IBMCloud.__name__: "IBM",
    GcpCloud.__name__: "GCP",
    # AWS.__name__: "AWS"
}


def log_resource_billing(user_id, project_id, resource):
    """Logs the resource for billing purposes"""

    try:
        cloud = eval(IBM_BILLING_RESOURCES_CLOUD_LIB[resource.__class__.__name__])
        log_resource = BillingResource(
            resource_type=IBM_BILLING_RESOURCES_LIB[resource.__class__.__name__],
            resource_data=resource.to_json(),
            user_id=user_id,
            project_id=project_id,
            cloud_id=cloud.id,
            cloud_type=CLOUD_TYPE_LIB[cloud.__class__.__name__],
            cloud_name=cloud.name
        )
        doosradb.session.add(log_resource)
        doosradb.session.commit()
    except KeyError:
        LOGGER.error(
            "Resource {} not registered for billing".format(resource.__class__.__name__)
        )
