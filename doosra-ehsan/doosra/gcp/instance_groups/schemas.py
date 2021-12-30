add_instance_group_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "region": {"type": "string", "minLength": 1},
        "zone": {"type": "string", "minLength": 1},
        "cloud_project_id": {"type": "string", "minLength": 1},
        "vpc_id": {"type": "string", "minLength": 1},
        "instances": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "instance_id": {"type": "string", "minLength": 1},
                },
                "required": ["instance_id"]
            }
        },
    },
    "required": ["name", "zone", "cloud_project_id", "vpc_id"]
}
