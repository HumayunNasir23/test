add_firewall_rule_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 255},
        "description": {"type": "string", "minLength": 1, "maxLength": 1024},
        "cloud_project_id": {"type": "string", "minLength": 1},
        "direction": {"type": "string", "minLength": 1},
        "action": {"type": "string", "minLength": 1},
        "priority": {"type": "string", "minLength": 1},
        "vpc_network_id": {"type": "string", "minLength": 1},
        "tags": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
            }},
        "ip_ranges": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
            }},
        "target_tags": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
            }},
        "ip_protocols": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "protocol": {"type": "string", "minLength": 1},
                    "ports": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "string",
                        }
                    },
                }
            },
        },
    },
    "required": ["name", "cloud_project_id", "vpc_network_id", "direction", "action"]
}
