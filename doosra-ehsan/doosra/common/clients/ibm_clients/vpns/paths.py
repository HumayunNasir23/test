LIST_IKE_POLICIES = "ike_policies"
CREATE_IKE_POLICY = "ike_policies"
DELETE_IKE_POLICY = "ike_policies/{ike_policy_id}"
GET_IKE_POLICY = "ike_policies/{ike_policy_id}"
UPDATE_IKE_POLICY = "ike_policies/{ike_policy_id}"

LIST_CONNECTION_USING_SPECIFIED_IKE_POLICY = "ike_policies/{ike_policy_id}/connections"

LIST_IPSEC_POLICIES = "ipsec_policies"
CREATE_IPSEC_POLICY = "ipsec_policies"
DELETE_IPSEC_POLICY = "ipsec_policies/{ipsec_policy_id}"
GET_IPSEC_POLICY = "ipsec_policies/{ipsec_policy_id}"
UPDATE_IPSEC_POLICY = "ipsec_policies/{ipsec_policy_id}"
LIST_CONNECTION_USING_SPECIFIED_IPSEC_POLICY = "ipsec_policies/{ipsec_policy_id}/connections"

LIST_VPN_GATEWAYS = "vpn_gateways"
CREATE_VPN_GATEWAYS = "vpn_gateways"
DELETE_VPN_GATEWAYS = "vpn_gateways/{vpn_gateway_id}"
GET_VPN_GATEWAYS = "vpn_gateways/{vpn_gateway_id}"
UPDATE_VPN_GATEWAY = "vpn_gateways/{vpn_gateway_id}"

LIST_CONNECTIONS_OF_VPN_GATEWAY = "vpn_gateways/{vpn_gateway_id}/connections"
CREATE_VPN_CONNECTION = "vpn_gateways/{vpn_gateway_id}/connections"
DELETE_VPN_CONNECTION = "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}"
GET_VPN_CONNECTION = "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}"
UPDATE_VPN_CONNECTION = "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}"

LIST_LOCAL_CIDR = "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/local_cidrs"
REMOVE_LOCAL_CIDR = \
    "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/local_cidrs/{prefix_address}/{prefix_length}"
CHECK_SPECIFIC_LOCAL_CIDR_EXISTS = \
    "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/local_cidrs/{prefix_address}/{prefix_length}"
SET_LOCAL_CIDR = \
    "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/local_cidrs/{prefix_address}/{prefix_length}"

LIST_PEER_CIDR = "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/peer_cidrs"
REMOVE_PEER_CIDR = \
    "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/peer_cidrs/{prefix_address}/{prefix_length}"
CHECK_SPECIFIC_PEER_CIDR_EXISTS = \
    "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/peer_cidrs/{prefix_address}/{prefix_length}"
SET_PEER_CIDR = \
    "vpn_gateways/{vpn_gateway_id}/connections/{connection_id}/peer_cidrs/{prefix_address}/{prefix_length}"
