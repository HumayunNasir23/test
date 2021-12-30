ibm_security_group_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "resource_group": {"type": "string", "minLength": 1},
        "vpc_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "direction": {"type": "string", "pattern": "^(inbound|outbound)$"},
                    "protocol": {"type": "string", "enum": ["tcp", "all", "udp", "http"]},
                    "address": {"type": "string", "format": "ipv4"},
                    "cidr_block": {"type": "string", "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$"},
                    "security_group": {"type": "string", "minLength": 1},
                    "port_min": {"type": "integer", "minLength": 1},
                    "port_max": {"type": "integer", "minLength": 1},
                    "code": {"type": "integer", "minLength": 1},
                    "type": {"type": "integer", "minLength": 1},
                },
                "required": ["direction", "protocol"]
            }
        },
    },
    "required": ["name", "resource_group", "vpc_id", "cloud_id"]
}

ibm_create_security_rule_rule_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {
            "type": "string",
            "minLength": 32,
            "maxLength": 32
        },
        "direction": {
            "type": "string",
            "pattern": "^(inbound|outbound)$"
        },
        "address": {
            "type": "string",
            "format": "ipv4",
        },
        "protocol": {
            "type": "string",
            "Enum": ["all", "tcp", "udp", "icmp"]
        },
        "cidr_block": {
            "type": "string",
            "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$"
        },
        "security_group": {
            "type": "string",
            "minLength": 1
        },
        "port_min": {
            "type": "integer",
            "minLength": 1
        },
        "port_max": {
            "type": "integer",
            "minLength": 1
        },
        "code": {
            "type": "integer",
            "minLength": 1
        },
        "type": {
            "type": "integer",
            "minLength": 1
        },

    },
    "required": ["direction", "protocol", "cloud_id"]
}
