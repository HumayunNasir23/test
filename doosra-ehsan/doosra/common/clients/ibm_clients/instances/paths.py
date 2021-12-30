LIST_INSTANCE_PROFILES_PATH = "instance/profiles"
GET_INSTANCE_PROFILE_PATH = "instance/profiles/{instance_profile_name}"

LIST_INSTANCES_PATH = "instances"
CREATE_INSTANCE_PATH = "instances"
DELETE_INSTANCE_PATH = "instances/{instance_id}"
GET_INSTANCE_PATH = "instances/{instance_id}"
UPDATE_INSTANCE_PATH = "instances/{instance_id}"

GET_INSTANCE_INIT_CONFIG_PATH = "instances/{instance_id}/initialization"

CREATE_INSTANCE_ACTION_PATH = "instances/{instance_id}/actions"

LIST_INSTANCE_NETWORK_INTERFACES_PATH = "instances/{instance_id}/network_interfaces"
CREATE_INSTANCE_NETWORK_INTERFACE_PATH = "instances/{instance_id}/network_interfaces"
DELETE_INSTANCE_NETWORK_INTERFACE_PATH = "instances/{instance_id}/network_interfaces/{network_interface_id}"
GET_INSTANCE_NETWORK_INTERFACE_PATH = "instances/{instance_id}/network_interfaces/{network_interface_id}"
UPDATE_INSTANCE_NETWORK_INTERFACE_PATH = "instances/{instance_id}/network_interfaces/{network_interface_id}"

LIST_INSTANCE_FLOATING_IPS_PATH = "instances/{instance_id}/network_interfaces/{network_interface_id}/floating_ips"
DELETE_INSTANCE_FLOATING_IP_PATH = \
    "instances/{instance_id}/network_interfaces/{network_interface_id}/floating_ips/{floating_ip_id}"
GET_INSTANCE_FLOATING_IP_PATH = \
    "instances/{instance_id}/network_interfaces/{network_interface_id}/floating_ips/{floating_ip_id}"
UPDATE_INSTANCE_FLOATING_IP_PATH = \
    "instances/{instance_id}/network_interfaces/{network_interface_id}/floating_ips/{floating_ip_id}"

LIST_INSTANCE_VOLUME_ATTACHMENTS_PATH = "instances/{instance_id}/volume_attachments"
CREATE_INSTANCE_VOLUME_ATTACHMENT_PATH = "instances/{instance_id}/volume_attachments"
DELETE_INSTANCE_VOLUME_ATTACHMENT_PATH = "instances/{instance_id}/volume_attachments/{volume_attachment_id}"
GET_INSTANCE_VOLUME_ATTACHMENT_PATH = "instances/{instance_id}/volume_attachments/{volume_attachment_id}"
UPDATE_INSTANCE_VOLUME_ATTACHMENT_PATH = "instances/{instance_id}/volume_attachments/{volume_attachment_id}"
