ibm_create_floating_ip_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {"type": "string", "minLength": 1},
        "resource_group": {"type": "string", "minLength": 1},
        "zone": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "region": {"type": "string", "minLength": 1},
    },
    "required": ["cloud_id", "resource_group", "zone", "region"]
}
