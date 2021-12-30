ibm_create_ssh_key_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "public_key": {"type": "string",
                       "pattern": "^ssh-rsa([^\/?#]*)([^?#]*)(\?([^#]*))?(#(.*))?$",
                       "minLength": 1},
        "cloud_id": {"type": "string", "minLength": 1},
        "resource_group": {"type": "string", "minLength": 1},
        "region": {"type": "string", "minLength": 1},
        "type": {"type": "string", "enum": ["rsa"], "minLength": 1}
    },
    "required": ["name", "public_key", "cloud_id", "resource_group", "region"]
}
