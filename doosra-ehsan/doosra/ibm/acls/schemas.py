ibm_create_acl_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "region": {"type": "string", "minLength": 1},
        "resource_group": {"type": "string", "minLength": 1},

        "subnets": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string"
            }
        },

        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                             "maxLength": 63},
                    "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
                    "action": {"type": "string", "pattern": "^(allow|deny)$"},
                    "direction": {"type": "string", "pattern": "^(inbound|outbound)$"},
                    "destination": {
                        "type": "string",
                        "pattern": "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(3[0-2]|[1-2][0-9]|[0-9]))?$"
                    },
                    "source": {
                        "type": "string",
                        "pattern": "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(3[0-2]|[1-2][0-9]|[0-9]))?$"
                    },

                    "protocol": {
                        "type": "string",
                        "Enum": ["all", "tcp", "udp"]
                    },
                    "source_port_max": {"type": "string", "minLength": 1},
                    "source_port_min": {"type": "string", "minLength": 1},
                    "destination_port_min": {"type": "string", "minLength": 1},
                    "destination_port_max": {"type": "string", "minLength": 1},
                    "code": {"type": "string", "minLength": 1},
                    "type": {"type": "string", "minLength": 1}
                },
                "required": ["name", "action", "direction", "protocol"]
            }
        },
    },
    "required": ["name", "region", "cloud_id", "resource_group"]
}

ibm_create_acl_rule_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "action": {"type": "string", "pattern": "^(allow|deny)$"},
        "direction": {"type": "string", "pattern": "^(inbound|outbound)$"},
        "destination": {
            "type": "string",
            "pattern": "^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        },
        "source": {
            "type": "string",
            "pattern": "^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        },

        "protocol": {
            "type": "string",
            "Enum": ["all", "tcp", "udp"]
        },
        "source_port_max": {"type": "string", "minLength": 1},
        "source_port_min": {"type": "string", "minLength": 1},
        "destination_port_min": {"type": "string", "minLength": 1},
        "destination_port_max": {"type": "string", "minLength": 1},
        "code": {"type": "string", "minLength": 1},
        "type": {"type": "string", "minLength": 1}
    },
    "required": ["name", "action", "direction", "protocol", "cloud_id"]
}
