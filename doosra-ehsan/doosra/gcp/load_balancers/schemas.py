add_load_balancer_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "cloud_project_id": {"type": "string", "minLength": 1},
        "frontends": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "ip_version": {"type": "string", "minLength": 1},
                    "ip_address": {"type": "string", "minLength": 1},
                    "protocol": {"type": "string", "minLength": 1},
                    "port_range": {"type": "string", "minLength": 1},
                },
                "required": ["name", "ip_version", "protocol", "port_range"],
            },
        },
        "host_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "hosts": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "paths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "backend_service": {"type": "string", "minLength": 1},
                },
                "required": ["backend_service", "hosts"]
            },
        },
        "backend_services": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "backend_service_id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "protocol": {"type": "string", "minLength": 1},
                    "port": {"type": "string", "minLength": 1},
                    "timeout": {"type": "string", "minLength": 1},
                    "backends": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "description": {"type": "string", "minLength": 1},
                                "instance_group_id": {"type": "string", "minLength": 1},
                                "max_cpu_utilization": {"type": "string", "minLength": 1},
                                "capacity_scaler": {"type": "string", "minLength": 1},

                            },
                            "required": ["instance_group_id"]
                        }
                    },
                    "health_check": {
                        "type": "object",
                        "properties": {
                            "health_check_id": {"type": "string", "minLength": 1},
                            "name": {"type": "string", "minLength": 1},
                            "description": {"type": "string", "minLength": 1},
                            "protocol": {"type": "string", "minLength": 1},
                            "port": {"type": "string", "minLength": 1},
                            "request": {"type": "string", "minLength": 1},
                            "response": {"type": "string", "minLength": 1},
                            "proxy_header": {"type": "string", "minLength": 1},
                            "healthy_threshold": {"type": "string", "minLength": 1},
                            "unhealthy_threshold": {"type": "string", "minLength": 1},
                            "timeout": {"type": "string", "minLength": 1},
                            "check_interval": {"type": "string", "minLength": 1},
                        },
                        "required": ["name", "protocol", "port"]
                    },
                },
                "required": ["backends", "health_check"]
            }
        },
    },
    "required": ["name", "backend_services", "frontends", "cloud_project_id"]
}
