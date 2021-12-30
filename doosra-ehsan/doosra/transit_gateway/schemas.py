transit_gateway_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-zA-Z]|[a-zA-Z][-_a-zA-Z0-9]*[a-zA-Z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "is_global_route": {"type": "boolean", "pattern": "^(true|false)$"},
        "cloud_id": {"type": "string", "minLength": 1},
        "resource_group": {"type": "string", "minLength": 1},
        "location": {"type": "string", "minLength": 1},
        "connections": {
            "type": "array",
            "properties": {
                "name": {"type": "string", "pattern": "^([a-zA-Z]|[a-zA-Z][-_a-zA-Z0-9]*[a-zA-Z0-9])$", "minLength": 1,
                         "maxLength": 63},
                "vpc_id": {"type": "string", "minLength": 1, "default": None},
                "vpc_name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                             "maxLength": 63},
                "location": {"type": "string", "minLength": 1},
                "network_type": {"type": "string", "minLength": 1, "enum": ["vpc", "classic"]}
            }
        }
    },
    "required": ["name", "location", "cloud_id"]
}

transit_gateway_connection_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-zA-Z]|[a-zA-Z][-_a-zA-Z0-9]*[a-zA-Z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "cloud_id": {"type": "string", "minLength": 1},
        "vpc_id": {"type": "string", "minLength": 1, "default": None},
        "vpc_name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1, "maxLength": 63},
        "location": {"type": "string", "minLength": 1},
        "network_type": {"type": "string", "minLength": 1, "enum": ["vpc", "classic"]}
    },
    "required": ["name", "network_type", "cloud_id"]
}

update_transit_gateway_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^([a-zA-Z]|[a-zA-Z][-_a-zA-Z0-9]*[a-zA-Z0-9])$",
            "minLength": 1,
            "maxLength": 63
        },
        "is_global_route": {"type": "boolean", "pattern": "^(true|false)$"}
    },
    "additionalProperties": False
}

update_tg_connection_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^([a-zA-Z]|[a-zA-Z][-_a-zA-Z0-9]*[a-zA-Z0-9])$",
            "minLength": 1,
            "maxLength": 63
        }
    },
    "additionalProperties": False
}
