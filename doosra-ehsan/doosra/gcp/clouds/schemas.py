gcp_cloud_account_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1}
    },
    "required": ["name"]
}

gcp_cloud_update_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
    },
}
