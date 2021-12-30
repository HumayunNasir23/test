add_vpc_network_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "cloud_project_id": {"type": "string", "minLength": 1},
        "subnets": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "region": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "ip_range": {"type": "string", "minLength": 1},
                    "secondary_ip_ranges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "ip_range": {"type": "string", "minLength": 1},
                            },
                            "required": ["name", "ip_range"]
                        }
                    }
                },
                "required": ["name", "region", "ip_range"]
            }
        },
    },
    "required": ["name", "cloud_project_id"]
}

update_vpc_network_schema = {
    "type": "object",
    "properties": {
        "subnets": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "region": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "ip_range": {"type": "string", "minLength": 1},
                    "secondary_ip_ranges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "ip_range": {"type": "string", "minLength": 1},
                            },
                            "required": ["name", "ip_range"]
                        }
                    }
                },
                "required": ["name", "region", "ip_range"]
            }
        },
    },
}
