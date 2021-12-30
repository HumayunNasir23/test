ibm_cloud_account_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 63},
        "api_key": {"type": "string", "minLength": 1},
        "resource_instance_id": {"type": "string", "minLength": 1},
        "access_key_id": {"type": "string", "minLength": 1},
        "secret_access_key": {"type": "string", "minLength": 1}
    },
    "required": ["name", "api_key", "resource_instance_id"]
}

ibm_cloud_update_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1,
                 "maxLength": 63},
        "api_key": {"type": "string", "minLength": 1},
        "resource_instance_id": {"type": "string", "minLength": 1},
        "access_key_id": {"type": "string", "minLength": 1},
        "secret_access_key": {"type": "string", "minLength": 1}
    },
}

discovery_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {"type": "string", "minLength": 1},
    },
    "required": ["cloud_id"]
}

ibm_update_dashboard_setting_schema = {
    "type": "array",
    "minItems": 1,
    "uniqueItems": True,
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "pin_status": {"type": "boolean"}
        },
        "required": ["id", "pin_status"]
    }
}
