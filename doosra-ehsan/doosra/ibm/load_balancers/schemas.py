ibm_create_load_balancer_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "region": {"type": "string", "minLength": 1},
        "is_public": {"type": "boolean", "pattern": "^(true|false)$"},
        "resource_group": {"type": "string", "minLength": 1},
        "vpc_id": {"type": "string", "minLength": 1},
        "cloud_id": {"type": "string", "minLength": 1},
        "subnets": {
            "type": "array",
            "Items": {
                "type": "object",
                "minItems": 1,
                "id": {"type": "string"}
            },
            "required": ["id"]
        },
        "listeners": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                    "protocol": {"type": "string",
                                 "enum": ["http", "https", "tcp"], "minLength": 1},
                    "connection_limit": {"type": "integer", "minimum": 1, "maximum": 15000},
                    "default_pool": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                                     "maxLength": 63},
                },
                "required": ["port", "protocol", "default_pool"]
            }
        },
        "pools": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "algorithm": {"type": "string",
                                  "enum": ["least_connections", "round_robin", "weighted_round_robin"], "minLength": 1},
                    "protocol": {"type": "string", "enum": ["http", "tcp"], "minLength": 1},
                    "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                             "maxLength": 63},
                    "session_persistence": {"type": "string", "enum": ["source_ip"], "minLength": 1},
                    "health_monitor": {
                        "type": "object",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "delay": {"type": "integer", "minLength": 2, "maxLength": 60},
                                "max_retries": {"type": "integer", "minLength": 2, "maxLength": 10},
                                "timeout": {"type": "integer", "minLength": 2, "maxLength": 59},
                                "protocol": {"type": "string","enum": ["http", "tcp"], "minLength": 1},
                                "port": {"type": "integer", "minLength": 1, "maxLength": 65535},
                                "url_path": {"type": "string", "minLength": 1}
                            },
                            "required": ["delay", "max_retries", "timeout", "protocol", "url_path", "health_monitor"]
                        }
                    },
                    "members": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "port": {"type": "integer", "minLength": 1, "maxLength": 65535},
                                "instance_id": {"type": "string", "minLength": 1},
                                "weight": {"type": "integer", "minimum": 1},
                            },
                            "required": ["port", "instance_id"]
                        }
                    }
                },
                "required": ["name", "algorithm", "protocol", "health_monitor"]
            }
        },
    },
    "required": ["name", "region", "vpc_id", "cloud_id", "resource_group", "is_public", "subnets"]
}
