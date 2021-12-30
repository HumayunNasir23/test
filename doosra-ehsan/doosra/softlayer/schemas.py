softlayer_account_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "username": {"type": "string", "minLength": 1},
        "api_key": {"type": "string", "minLength": 1},
        "ibm_cloud_account_id": {"type": "string", "minLength": 1}
    },
    "required": ["name", "username", "api_key", "ibm_cloud_account_id"]
}

softlayer_account_update_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "username": {"type": "string", "minLength": 1},
        "api_key": {"type": "string", "minLength": 1},
        "ibm_cloud_account_id": {"type": "string", "minLength": 1}
    },
}
