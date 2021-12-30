ibm_image_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {
            "type": "string",
            "minLength": 32,
            "maxLength": 32
        },
        "name": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63
        },
        "resource_group": {
            "type": "string",
            "minLength": 1,
            "cloud_object_storage_instance": {
                "type": "string",
                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                "minLength": 1,
                "maxLength": 63
            },
            "region": {
                "type": "string",
                "minLength": 1
            },
            "bucket": {
                "type": "string",
                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                "minLength": 1,
                "maxLength": 63
            },
            "image_template": {
                "type": "string",
                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                "minLength": 1,
                "maxLength": 63
            },
            "operating_system": {
                "type": "string",
                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                "minLength": 1,
                "maxLength": 63
            },
        }
    },
    "required": ["name", "resource_group", "bucket", "image_template", "operating_system"],
}

ibm_image_migration_update_schema = {
    "type": "object",
    "properties": {
        "step": {"type": "string", "enum": ["DOWNLOAD", "CONVERT", "VALIDATE", "UPLOAD"]},
        "status": {"type": "string", "enum": ["SUCCESSFUL", "FAILED"]},
        "message": {"type": "string"}
    },
    "required": ["step", "status", "message"]
}
