add_instance_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "zone": {"type": "string", "minLength": 1},
        "machine_type": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "cloud_project_id": {"type": "string", "minLength": 1},
        "network_tags": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
            }},
        "interfaces": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "vpc_id": {"type": "string", "minLength": 1},
                    "subnetwork_id": {"type": "string", "minLength": 1},
                    "primary_internal_ip": {"type": "string", "minLength": 1},
                    "external_ip": {"type": "string", "minLength": 1}
                },
                "required": ["name", "vpc_id", "subnetwork_id"]
            }
        },
        "disks": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "type": {"type": "string", "minLength": 1},
                    "size": {"type": "string", "minLength": 1},
                    "source_image": {"type": "string", "minLength": 1},
                    "mode": {"type": "string", "minLength": 1},
                    "boot": {"type": "boolean"},
                    "auto_delete": {"type": "boolean"},

                },
                "required": ["name"]
            }
        },
    },
    "required": ["name", "cloud_project_id", "network_tags", "zone", "interfaces"]
}
