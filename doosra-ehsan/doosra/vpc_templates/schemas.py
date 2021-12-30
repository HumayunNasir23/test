add_template_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "cloud_type": {"type": "string", "minLength": 1},
        "schema_type": {"type": "string", "minLength": 1},
        "schema": {"type": "string", "minLength": 1}
    },
    "required": ["name", "schema", "cloud_type", "schema_type"]
}

update_template_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "cloud_type": {"type": "string", "minLength": 1},
        "schema_type": {"type": "string", "minLength": 1},
        "schema": {"type": "string", "minLength": 1}
    },
}
