add_content_migration_meta_data_schema = {
    "type": "object",
    "properties": {
        "user_id": {"type": "string", "minLength": 1,
                    "maxLength": 63},
        "ip": {"type": "string",
               "pattern": "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"},
        "hostname": {"type": "string", "minLength": 1},
        "disks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "disk_name": {"type": "string"},
                    "size": {"type": "string"},
                    "fstype": {"type": "string"},
                    "mountpoint": {"type": "string"},
                    "has_partitions": {"type": "boolean", "pattern": "^(true|false)$"},
                    "partitions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "disk_name": {"type": "string"},
                                "fstype": {"type": "string"},
                                "mountpoint": {"type": "string"},
                                "sub_partitions": {"type": "boolean", "pattern": "^(true|false)$"},
                                "size": {"type": "string"},
                                "parttype": {"type": "string", "enum": ["Extended", "Linux"], "default": "Linux",
                                             "minLength": 1},
                                "partitions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "disk_name": {"type": "string"},
                                            "fstype": {"type": "string"},
                                            "mountpoint": {"type": "string"},
                                            "size": {"type": "string"},
                                            "parttype": {"type": "string", "enum": ["Extended", "Linux"],
                                                         "default": "Linux",
                                                         "minLength": 1},
                                        },
                                        "required": ["disk_name", "fstype", "mountpoint", "size", "parttype"]
                                    }
                                }
                            },
                            "anyOf": [
                                {"required": ["disk_name", "size", "fstype", "parttype", "mountpoint"]},
                                {"required": ["disk_name", "size", "fstype", "parttype", "partitions"]}],
                        }
                    }},
                "anyOf": [
                    {"required": ["disk_name", "size", "fstype", "has_partitions", "mountpoint"]},
                    {"required": ["disk_name", "size", "fstype", "has_partitions", "partitions"]},
                ],
            }
        },
    },
    "required": ["user_id", "ip", "hostname", "disks"]
}

start_nas_migration_schema = {
    "type": "object",
    "properties": {
        "src_migrator": {"type": "string", "minLength": 1},
        "trg_migrator": {"type": "string", "minLength": 1},
        "locations": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
            }}
    },
    "required": ["src_migrator", "trg_migrator", "locations"]

}
