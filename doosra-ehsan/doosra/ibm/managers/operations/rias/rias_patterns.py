# RESOURCE CREATION PATTERNS
CREATE_ADDRESS_PREFIX_PATTERN = [
    "POST", "{{base_url}}/v1/vpcs/{vpc_id}/address_prefixes?version={{version}}&generation={{generation}}"
]

CREATE_VPC_PATTERN = [
    "POST", "{{base_url}}/v1/vpcs?version={{version}}&generation={{generation}}"
]
CREATE_VPC_ROUTE_PATTERN = [
    "POST", "{{base_url}}/v1/vpcs/{vpc_id}/routes?version={{version}}&generation={{generation}}"
]
CREATE_INSTANCE_PATTERN = [
    "POST", "{{base_url}}/v1/instances?version={{version}}&generation={{generation}}"
]

CREATE_INSTANCE_ACTION_PATTERN = [
    "POST", "{{base_url}}/v1/instances/{instance_id}/actions?version={{version}}&generation={{generation}}"
]

CREATE_SECURITY_GROUP_PATTERN = [
    "POST", "{{base_url}}/v1/security_groups?version={{version}}&generation={{generation}}"
]

CREATE_SECURITY_GROUP_RULE_PATTERN = [
    "POST", "{{base_url}}/v1/security_groups/{security_group_id}/rules?version={{version}}&generation={{generation}}"
]

CREATE_SUBNET_PATTERN = [
    "POST", "{{base_url}}/v1/subnets?version={{version}}&generation={{generation}}"
]

CREATE_SSH_KEY_PATTERN = [
    "POST", "{{base_url}}/v1/keys?version={{version}}&generation={{generation}}"
]

CREATE_IMAGE = [
    "POST", "{{base_url}}/v1/images?version={{version}}&generation={{generation}}"
]

CREATE_FLOATING_IP_PATTERN = [
    "POST", "{{base_url}}/v1/floating_ips?version={{version}}&generation={{generation}}"
]

CREATE_ACL_PATTERN = [
    "POST", "{{base_url}}/v1/network_acls?version={{version}}&generation={{generation}}"
]

CREATE_ACL_RULE_PATTERN = [
    "POST", "{{base_url}}/v1/network_acls/{acl_id}/rules?version={{version}}&generation={{generation}}"
]

CREATE_PUBLIC_GATEWAY_PATTERN = [
    "POST", "{{base_url}}/v1/public_gateways?version={{version}}&generation={{generation}}"
]

CREATE_IKE_POLICY = [
    "POST", "{{base_url}}/v1/ike_policies?version={{version}}&generation={{generation}}"
]

CREATE_IPSEC_POLICY = [
    "POST", "{{base_url}}/v1/ipsec_policies?version={{version}}&generation={{generation}}"
]

CREATE_VPN_GATEWAY_PATTERN = [
    "POST", "{{base_url}}/v1/vpn_gateways?version={{version}}&generation={{generation}}"
]

CREATE_VPN_CONNECTION = [
    "POST", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections?version={{version}}&generation={{generation}}"
]

CREATE_K8S_CLUSTER_PATTERN = [
    "POST", "{{k8s_base_url}}/v2/vpc/createCluster"
]

CREATE_K8S_WORKERPOOL_PATTERN =[
    "POST", "{{k8s_base_url}}/v2/vpc/createWorkerPool"
]

CREATE_LOAD_BALANCER_PATTERN = [
    "POST", "{{base_url}}/v1/load_balancers?version={{version}}&generation={{generation}}"
]

# RESOURCE UPDATION PATTERNS
ATTACH_ACL_TO_SUBNET_PATTERN = [
    "PUT", "{{base_url}}/v1/subnets/{subnet_id}/network_acl?version={{version}}&generation={{generation}}"
]

ATTACH_PUBLIC_GATEWAY_TO_SUBNET_PATTERN = [
    "PUT", "{{base_url}}/v1/subnets/{subnet_id}/public_gateway?version={{version}}&generation={{generation}}"
]

DETACH_PUBLIC_GATEWAY_TO_SUBNET_PATTERN = [
    "DELETE", "{{base_url}}/v1/subnets/{subnet_id}/public_gateway?version={{version}}&generation={{generation}}"
]

ATTACH_FLOATING_IP_TO_INTERFACE_PATTERN = [
    "PUT",
    "{{base_url}}/v1/instances/{instance_id}/network_interfaces/{network_interface_id}/floating_ips/{"
    "floating_ip_id}?version={{version}}&generation={{generation}}"
]

DETACH_FLOATING_IP_TO_INTERFACE_PATTERN = [
    "DELETE",
    "{{base_url}}/v1/instances/{instance_id}/network_interfaces/{network_interface_id}/floating_ips/{"
    "floating_ip_id}?version={{version}}&generation={{generation}}"
]

DETACH_NETWORK_INTERFACE_FROM_SECURITY_GROUP_PATTERN = [
    "DELETE",
    "{{base_url}}/v1/security_groups/{security_group_id}/network_interfaces/{network_interface_id}?version={{"
    "version}}&generation={{generation}}"
]

UPDATE_LOCAL_CIDR_VPN_CONNECTION = [
    "PUT", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{id}/local_cidrs/{prefix_address}/{prefix_length}"
           "?version={{version}}&generation={{generation}}"
]

UPDATE_PEER_CIDR_VPN_CONNECTION = [
    "PUT", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{id}/peer_cidrs/{prefix_address}/{prefix_length}"
           "?version={{version}}&generation={{generation}}"
]

# RESOURCE DELETION PATTERNS
DELETE_K8S_CLUSTER_PATTERN = [
    "DELETE", "{{k8s_base_url}}/v1/clusters/{cluster}"
]

DELETE_ADDRESS_PREFIX_PATTERN = [
    "DELETE",
    "{{base_url}}/v1/vpcs/{vpc_id}/address_prefixes/{address_prefix_id}?version={{version}}&generation={{generation}}"
]

DELETE_VPC_PATTERN = [
    "DELETE", "{{base_url}}/v1/vpcs/{vpc_id}?version={{version}}&generation={{generation}}"
]

DELETE_VPC_ROUTE_PATTERN = [
    "DELETE", "{{base_url}}/v1/vpcs/{vpc_id}/routes/{route_id}?version={{version}}&generation={{generation}}"
]

DELETE_INSTANCE_PATTERN = [
    "DELETE", "{{base_url}}/v1/instances/{instance_id}?version={{version}}&generation={{generation}}"
]

DELETE_SUBNET_PATTERN = [
    "DELETE", "{{base_url}}/v1/subnets/{subnet_id}?version={{version}}&generation={{generation}}"
]

DELETE_IMAGE = [
    "DELETE", "{{base_url}}/v1/images/{image_id}?version={{version}}&generation={{generation}}"
]

DELETE_ACL_PATTERN = [
    "DELETE", "{{base_url}}/v1/network_acls/{acl_id}?version={{version}}&generation={{generation}}"
]

DELETE_ACL_RULE_PATTERN = [
    "DELETE", "{{base_url}}/v1/network_acls/{acl_id}/rules/{rule_id}?version={{version}}&generation={{generation}}"
]

DELETE_SECURITY_GROUP_PATTERN = [
    "DELETE", "{{base_url}}/v1/security_groups/{security_group_id}?version={{version}}&generation={{generation}}"
]

DELETE_SECURITY_GROUP_RULE_PATTERN = [
    "DELETE",
    "{{base_url}}/v1/security_groups/{security_group_id}/rules/{rule_id}?version={{version}}&generation={{generation}}"
]

DELETE_NETWORK_INTERFACE_PATTERN = [
    "DELETE",
    "{{base_url}}/v1/instances/{instance_id}/network_interfaces/{network_interface_id}?version={{"
    "version}}&generation={{generation}}"
]

DELETE_VOLUME_ATTACHMENT_PATTERN = [
    "DELETE",
    "{{base_url}}/v1/instances/{instance_id}/volume_attachments/{volume_attachment_id}?version={{"
    "version}}&generation={{generation}}"
]

DELETE_PUBLIC_GATEWAY_PATTERN = [
    "DELETE", "{{base_url}}/v1/public_gateways/{public_gateway_id}?version={{version}}&generation={{generation}}"
]

DELETE_SSH_KEY_PATTERN = [
    "DELETE", "{{base_url}}/v1/keys/{ssh_key_id}?version={{version}}&generation={{generation}}"
]

DELETE_IKE_POLICY = [
    "DELETE", "{{base_url}}/v1/ike_policies/{ike_policy_id}?version={{version}}&generation={{generation}}"
]

DELETE_IPSEC_POLICY = [
    "DELETE", "{{base_url}}/v1/ipsec_policies/{ipsec_policy_id}?version={{version}}&generation={{generation}}"
]

DELETE_VPN_GATEWAY = [
    "DELETE", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}?version={{version}}&generation={{generation}}"
]
DELETE_VPN_CONNECTION = [
    "DELETE",
    "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{connection_id}?version={{version}}&generation={{"
    "generation}}"
]
DELETE_FLOATING_IP_PATTERN = [
    "DELETE", "{{base_url}}/v1/floating_ips/{floating_ip_id}?version={{version}}&generation={{generation}}"
]

DELETE_LOAD_BALANCER_LISTENER_PATTERN = [
    "DELETE", "{{base_url}}/v1/load_balancers/{load_balancer_id}/listeners/{listener_id}?version={{"
              "version}}&generation={ "
              "{generation}}"
]

DELETE_VOLUME_PATTERN = [
    "DELETE", "{{base_url}}/v1/volumes/{volume_id}?version={{version}}&generation={{generation}}"
]

DELETE_LOAD_BALANCER_PATTERN = [
    "DELETE", "{{base_url}}/v1/load_balancers/{load_balancer_id}?version={{version}}&generation={{generation}}"
]

DELETE_VPN_LOCAL_CIDR_PATTERN = [
    "DELETE", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{id}/local_cidrs/{prefix_address}/{prefix_length}"
              "?version={{version}}&generation={{generation}}"
]

DELETE_VPN_PEER_CIDR_PATTERN=[
    "DELETE", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{id}/peer_cidrs/{prefix_address}/{prefix_length}"
              "?version={{version}}&generation={{generation}}"
]

# RESOURCE FETCH PATTERNS
LIST_ADDRESS_PREFIXES_PATTERN = [
    "GET", "{{base_url}}/v1/vpcs/{vpc_id}/address_prefixes?version={{version}}&generation={{generation}}"
]

LIST_FLOATING_IPS_PATTERN = [
    "GET", "{{base_url}}/v1/floating_ips?version={{version}}&generation={{generation}}"
]

LIST_VPCS_PATTERN = [
    "GET", "{{base_url}}/v1/vpcs?version={{version}}&generation={{generation}}"
]

LIST_VPC_ROUTES = [
    "GET", "{{base_url}}/v1/vpcs/{vpc_id}/routes?version={{version}}&generation={{generation}}&{zone_name}"
]

LIST_SECURITY_GROUPS_PATTERN = [
    "GET", "{{base_url}}/v1/security_groups?version={{version}}&generation={{generation}}"
]

LIST_SECURITY_GROUP_RULES_PATTERN = [
    "GET", "{{base_url}}/v1/security_groups/{security_group_id}/rules?version={{version}}&generation={{generation}}"
]

LIST_SUBNETS_PATTERN = [
    "GET", "{{base_url}}/v1/subnets?version={{version}}&generation={{generation}}"
]

LIST_PUBLIC_GATEWAYS_PATTERN = [
    "GET", "{{base_url}}/v1/public_gateways?version={{version}}&generation={{generation}}"
]

LIST_REGIONS_PATTERN = [
    "GET", "{{base_url}}/v1/regions?version={{version}}&generation={{generation}}"
]

LIST_ZONES_PATTERN = [
    "GET", "{{base_url}}/v1/regions/{region}/zones?version={{version}}&generation={{generation}}"
]

LIST_ACLS_PATTERN = [
    "GET", "{{base_url}}/v1/network_acls?version={{version}}&generation={{generation}}"
]

LIST_ACL_RULES_PATTERN = [
    "GET", "{{base_url}}/v1/network_acls/{acl_id}/rules?version={{version}}&generation={{generation}}"
]

LIST_IKE_POLICIES = [
    "GET", "{{base_url}}/v1/ike_policies?version={{version}}&generation={{generation}}"
]

LIST_IPSEC_POLICIES = [
    "GET", "{{base_url}}/v1/ipsec_policies?version={{version}}&generation={{generation}}"
]
LIST_VPN_GATEWAYS_PATTERN = [
    "GET", "{{base_url}}/v1/vpn_gateways?version={{version}}&generation={{generation}}"
]
LIST_VPN_GATEWAY_CONNECTIONS_PATTERN = [
    "GET", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections?version={{version}}&generation={{generation}}"
]

LIST_INSTANCES_PATTERN = [
    "GET", "{{base_url}}/v1/instances?version={{version}}&generation={{generation}}"
]

LIST_IMAGES_PATTERN = [
    "GET", "{{base_url}}/v1/images?limit=100&version={{version}}&generation={{generation}}"
]

LIST_OPERATING_SYSTEMS_PATTERN = [
    "GET", "{{base_url}}/v1/operating_systems?version={{version}}&generation={{generation}}"
]

LIST_INSTANCE_PROFILES_PATTERN = [
    "GET", "{{base_url}}/v1/instance/profiles?version={{version}}&generation={{generation}}"
]

LIST_INSTANCE_NETWORK_INTERFACES_PATTERN = [
    "GET", "{{base_url}}/v1/instances/{instance_id}/network_interfaces?version={{version}}&generation={{generation}}"
]

LIST_SSH_KEYS_PATTERN = [
    "GET", "{{base_url}}/v1/keys?version={{version}}&generation={{generation}}"
]

LIST_VOLUMES_PATTERN = [
    "GET", "{{base_url}}/v1/volumes?version={{version}}&generation={{generation}}"
]

LIST_VOLUME_PROFILES_PATTERN = [
    "GET", "{{base_url}}/v1/volume/profiles?version={{version}}&generation={{generation}}"
]

LIST_LOAD_BALANCERS_PATTERN = [
    "GET", "{{base_url}}/v1/load_balancers?version={{version}}&generation={{generation}}"
]

LIST_LOAD_BALANCERS_LISTENERS_PATTERN = [
    "GET", "{{base_url}}/v1/load_balancers/{load_balancer_id}/listeners/?version={{version}}&generation={{generation}}"
]

LIST_LOAD_BALANCERS_POOLS_PATTERN = [
    "GET", "{{base_url}}/v1/load_balancers/{load_balancer_id}/pools/?version={{version}}&generation={{generation}}"
]

LIST_POOL_MEMBERS_PATTERN = [
    "GET",
    "{{base_url}}/v1/load_balancers/{load_balancer_id}/pools/{pool_id}/members?version={{version}}&generation={{"
    "generation}}"
]

LIST_K8S_CLUSTERS_PATTERN = [
    "GET", "{{k8s_base_url}}/v2/vpc/getClusters"
]

GET_K8S_CLUSTERS_DETAIL = [
    "GET", "{{k8s_base_url}}/v2/vpc/getCluster?cluster={cluster}&showResources=true"
]

GET_K8S_CLUSTERS_WORKER_POOL = [
    "GET", "{{k8s_base_url}}/v2/vpc/getWorkerPools?cluster={cluster}"
]

GET_K8S_WORKERPOOL_WORKERS = [
    "GET", "{{k8s_base_url}}/v2/vpc/getWorkers?cluster={cluster}&showDeleted={showDeleted}&pool={workerpool}"
]

GET_INSTANCE_SSH_KEYS_PATTERN = [
    "GET", "{{base_url}}/v1/instances/{instance_id}/initialization?version={{version}}&generation={{generation}}"
]

GET_ACL_PATTERN = [
    "GET", "{{base_url}}/v1/network_acls/{acl_id}?version={{version}}&generation={{generation}}"
]

GET_ACL_RULE_PATTERN = [
    "GET", "{{base_url}}/v1/network_acls/{acl_id}/rules/{rule_id}?version={{version}}&generation={{generation}}"
]

GET_PUBLIC_GATEWAY_PATTERN = [
    "GET", "{{base_url}}/v1/public_gateways/{public_gateway_id}?version={{version}}&generation={{generation}}"
]

GET_SUBNET_PATTERN = [
    "GET", "{{base_url}}/v1/subnets/{subnet_id}?version={{version}}&generation={{generation}}"
]

GET_VPC_PATTERN = [
    "GET", "{{base_url}}/v1/vpcs/{vpc_id}?version={{version}}&generation={{generation}}"
]

GET_VPC_ROUTE_PATTERN = [
    "GET", "{{base_url}}/v1/vpcs/{vpc_id}/routes/{route_id}?version={{version}}&generation={{generation}}"
]

GET_INSTANCE_PATTERN = [
    "GET", "{{base_url}}/v1/instances/{instance_id}?version={{version}}&generation={{generation}}"
]

GET_LOAD_BALANCER_PATTERN = [
    "GET", "{{base_url}}/v1/load_balancers/{load_balancer_id}?version={{version}}&generation={{generation}}"
]

GET_VPN_GATEWAY_PATTERN = [
    "GET", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}?version={{version}}&generation={{generation}}"
]

GET_IKE_POLICY_PATTERN = [
    "GET", "{{base_url}}/v1/ike_policies/{ike_policy_id}?version={{version}}&generation={{generation}}"
]

GET_IPSEC_POLICY_PATTERN = [
    "GET", "{{base_url}}/v1/ipsec_policies/{ipsec_policy_id}?version={{version}}&generation={{generation}}"
]

GET_VPN_CONNECTION_PATTERN = [
    "GET", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{connection_id}?version={{version}}&generation={"
           "{generation}}"
]
GET_LOAD_BALANCER_LISTENER_PATTERN = [
    "GET", "{{base_url}}/v1/load_balancers/{load_balancer_id}/listeners/{listener_id}?version={{"
           "version}}&generation={{generation}}"
]

GET_DEFAULT_SECURITY_GROUP_PATTERN = [
    "GET", "{{base_url}}/v1/vpcs/{vpc_id}/default_security_group?version={{version}}&generation={{generation}}"
]

GET_SSH_KEY_PATTERN = [
    "GET", "{{base_url}}/v1/keys/{ssh_key_id}?version={{version}}&generation={{generation}}"
]

GET_ATTACHED_PUBLIC_GATEWAY_PATTERN = [
    "GET", "{{base_url}}/v1/subnets/{subnet_id}/public_gateway?version={{version}}&generation={{generation}}"
]

GET_INTERFACE_FLOATING_IP_PATTERN = [
    "GET",
    "{{base_url}}/v1/instances/{instance_id}/network_interfaces/{network_interface_id}/floating_ips?version={{"
    "version}}&generation={{generation}}"
]

GET_NETWORK_INTERFACE_PATTERN = [
    "GET",
    "{{base_url}}/v1/instances/{instance_id}/network_interfaces/{network_interface_id}?version={{"
    "version}}&generation={{generation}}"
]

GET_IMAGE_PATTERN = [
    "GET", "{{base_url}}/v1/images/{image_id}?version={{version}}&generation={{generation}}"
]

GET_FLOATING_IP_PATTERN = [
    "GET", "{{base_url}}/v1/floating_ips/{floating_ip_id}?version={{version}}&generation={{generation}}"
]

GET_VOLUME_PATTERN = [
    "GET", "{{base_url}}/v1/volumes/{volume_id}?version={{version}}&generation={{generation}}"
]

GET_SECURITY_GROUP_PATTERN = [
    "GET", "{{base_url}}/v1/security_groups/{security_group_id}?version={{version}}&generation={{generation}}"
]

GET_SECURITY_GROUP_RULE_PATTERN = [
    "GET",
    "{{base_url}}/v1/security_groups/{security_group_id}/rules/{rule_id}?version={{version}}&generation={{generation}}"
]

GET_ADDRESS_PREFIXES_PATTERN = [
    "GET", "{{base_url}}/v1/vpcs/{vpc_id}/address_prefixes/{address_prefix_id}?version={{version}}&generation={{"
           "generation}}"
]

GET_LOCAL_CIDRS_VPN_CONNECTION = [
    "GET", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{id}/local_cidrs/{prefix_address}/{prefix_length}"
           "?version={{version}}&generation={{generation}}"
]

GET_PEER_SUBNET_VPN_CONNECTION = [
    "GET", "{{base_url}}/v1/vpn_gateways/{vpn_gateway_id}/connections/{id}/peer_cidrs/{prefix_address}/{prefix_length}"
           "?version={{version}}&generation={{generation}}"
]
