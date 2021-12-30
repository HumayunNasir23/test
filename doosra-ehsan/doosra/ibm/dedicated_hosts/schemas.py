ibm_create_dedicated_host_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "region": {"type": "string", "minLength": 1},
        "zone": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "instance_placement_enabled": {"type": "boolean"},
        "resource_group": {"type": "string", "minLength": 1},
        "dedicated_host_profile": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "minLength": 32, "maxLength": 32}
            },
            "required": ["id"]
        },
        "dedicated_host_group_name":
            {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "dedicated_host_group": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                    "minLength": 1,
                    "maxLength": 63
                },
                "resource_group": {"type": "string", "minLength": 1}
            }
        }
    },
    "required": ["region", "zone", "cloud_id", "dedicated_host_profile"]
}

ibm_delete_dedicated_host_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "region": {"type": "string", "minLength": 1},
    },
    "required": ["cloud_id", "region"]
}

ibm_create_dedicated_host_group_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "class": {"type": "string", "minLength": 1},
        "family": {"type": "string", "enum": ["memory", "balanced", "compute"], "default": "balanced", "minLength": 1},
        "zone": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "region": {"type": "string", "minLength": 1},
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "resource_group": {"type": "string", "minLength": 1},
    },
    "required": ["cloud_id", "region", "zone", "class", "family"]
}

ibm_delete_dedicated_host_group_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "region": {"type": "string", "minLength": 1},
    },
    "required": ["cloud_id", "region"]
}

ibm_sync_dh_profiles_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "region": {"type": "string", "minLength": 1},
    },
    "required": ["cloud_id", "region"]
}
