LIST_SECURITY_GROUPS = "security_groups"
CREATE_SECURITY_GROUP = "security_groups"
DELETE_SECURITY_GROUP = "security_groups/{security_group_id}"
GET_SECURITY_GROUP = "security_groups/{security_group_id}"
UPDATE_SECURITY_GROUP = "security_groups/{security_group_id}"

LIST_SECURITY_GROUP_NETWORK_INTERFACE = "security_groups/{security_group_id}/network_interfaces"
REMOVE_NETWORK_INTERFACE_FROM_SECURITY_GROUP = \
    "security_groups/{security_group_id}/network_interfaces/{network_interface_id}"
GET_NETWORK_INTERFACE_IN_SECURITY_GROUP = \
    "security_groups/{security_group_id}/network_interfaces/{network_interface_id}"
ADD_NETWORK_INTERFACE_TO_SECURITY_GROUP = \
    "security_groups/{security_group_id}/network_interfaces/{network_interface_id}"

LIST_SECURITY_GROUPS_RULES = "security_groups/{security_group_id}/rules"
CREATE_SECURITY_GROUPS_RULES = "security_groups/{security_group_id}/rules"
DELETE_SECURITY_GROUPS_RULES = "security_groups/{security_group_id}/rules/{rule_id}"
GET_SECURITY_GROUPS_RULES = "security_groups/{security_group_id}/rules/{rule_id}"
UPDATE_SECURITY_GROUP_RULES = "security_groups/{security_group_id}/rules/{rule_id}"
