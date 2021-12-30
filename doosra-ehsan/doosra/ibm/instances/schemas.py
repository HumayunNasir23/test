ibm_instance_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "zone": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "resource_group": {"type": "string", "minLength": 1},
        "dedicated_host_name":
            {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "dedicated_host_group_name":
            {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "vpc_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "encryption": {"type": "string", "default": "provider_managed", "minLength": 1},
        "instance_profile": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                             "maxLength": 63},
        "image": {
            "type": "object",
            "properties": {
                "image_location": {"type": "string",
                                   "pattern": "^(classical_vsi|classical_image|cos_vhd|cos_vmdk|cos_qcow2|custom_image|public_image)$"},
                "classical_account_id": {"type": "string", "minLength": 1},
                "classical_instance_id": {"type": "integer", "minimum": 1},
                "classical_image_id": {"type": "integer", "minimum": 1},
                "bucket_name": {"type": "string", "minLength": 1},
                "bucket_object": {"type": "string", "minLength": 1},
                "image_name": {"type": "string", "minLength": 1},
                "custom_image": {"type": "string", "minLength": 1},
                "public_image": {"type": "string", "minLength": 1},
                "vpc_image_name": {"type": "string", "minLength": 1},
            },
            "required": ["image_location"],
        },
        "user_data": {"type": "string", "minLength": 1},
        "ssh_keys": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
            }},
        "network_interfaces":
            {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1, "maxLength": 63},
                        "subnet_id": {"type": "string", "minLength": 32, "maxLength": 32},
                        "security_groups": {
                            "type": "array",
                            "items": {"type": "string"},
                            "uniqueItems": True
                        }
                    },
                    "reserve_floating_ip": {"type": "boolean", "pattern": "^(true|false)$"},
                    "is_primary": {"type": "boolean", "pattern": "^(true|false)$"},
                },
                "required": ["name", "subnet_id", "security_group_id", "reserve_floating_ip", "is_primary"]
            },
        "volume_attachments":
            {
                "type": "array",
                "properties": {
                    "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                             "maxLength": 63},
                    "volume_profile_name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                            "minLength": 1,
                                            "maxLength": 63},
                    "iops": {"type": "string", "minLength": 1},
                    "capacity": {"type": "string", "minLength": 10, "maxLength": 2000},
                    "auto_delete": {"type": "boolean", "pattern": "^(true|false)$"},
                    "type": {"type": "string", "enum": ["boot", "data"], "default": "data", "minLength": 1},
                },
                "required": ["name", "volume_profile_name", "iops", "auto_delete", "capcacity"]
            },
    },
    "required": ["name", "zone", "resource_group", "vpc_id", "cloud_id", "image", "instance_profile",
                 "network_interfaces", "ssh_keys"]
}

secondary_volume_migration_schema = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "Enum": ["IN_PROGRESS", "FAILED", "SUCCESS", "CREATED", "BACKGROUND"],
        },
        "message": {"type": "string"},
    },
    "required": ["status"],
}

windows_secondary_volume_migration_schema = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "Enum": ["IN_PROGRESS", "FAILED", "SUCCESS"],
        },
        "message": {"type": "string"},
        "start_time": {"type": "string", "maxLength": 32},
        "end_time": {"type": "string", "maxLength": 32},
        "duration": {"type": "string", "maxLength": 32},
        "instance_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "action": {"type": "string"},
        "resources": {
            "type": "array",
            "properties": {
                "status": {
                    "type": "string",
                    "Enum": ["IN_PROGRESS", "PENDING", "FAILED", "SUCCESS"],
                },
                "message": {"type": "string"},
                "name": {"type": "string", "maxLength": 100},
                "size": {"type": "string", "maxLength": 32},
                "download_speed": {"type": "string", "maxLength": 32},
                "start_time": {"type": "string", "maxLength": 32},
                "end_time": {"type": "string", "maxLength": 32},
                "duration": {"type": "string", "maxLength": 32},
                "eta": {"type": "string", "maxLength": 32},
                "action": {"type": "string"},
                "trace": {"type": "string"},
            }
        }
    },
    "required": ["status", "instance_id", "resources"],
}
