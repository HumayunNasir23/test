ibm_public_gateway_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "vpc_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "resource_group": {"type": "string", "minLength": 1},
        "zone": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
    },
    "required": ["name", "zone", "vpc_id", "cloud_id", "resource_group"]
}
