ibm_ike_policy_schema = {
    "type": "object",
    "cloud_id": {"type": "string", "minLength": 1},
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "authentication_algorithm": {"type": "string", "enum": ["md5", "sha1", "sha256"], "minLength": 1},
        "dh_group": {"type": "integer", "enum": [2, 5, 14]},
        "encryption_algorithm": {"type": "string", "enum": ["triple_des", "aes128", "aes256"], "minLength": 1},
        "ike_version": {"type": "integer", "enum": [1, 2], "minimum": 1, "maximum": 2},
        "region": {"type": "string", "minLength": 1},
        "key_lifetime": {"type": "integer", "minimum": 1800, "maximum": 86400},
    },
    "required": ["name", "cloud_id", "authentication_algorithm", "dh_group", "encryption_algorithm",
                 "ike_version", "key_lifetime", "region"]
}

ibm_ipsec_policy_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "authentication_algorithm": {"type": "string", "enum": ["md5", "sha1", "sha256"], "minLength": 1},
        "region": {"type": "string", "minLength": 1},
        "pfs": {"type": "string", "enum": ["disabled", "group_14", "group_2", "group_5"], "minLength": 1, "maxLength": 8},
        "encryption_algorithm": {"type": "string", "enum": ["triple_des", "aes128", "aes256"], "minLength": 1},
        "key_lifetime": {"type": "integer", "minimum": 1800, "maximum": 86400},
    },
    "required": ["name", "cloud_id", "authentication_algorithm", "pfs", "encryption_algorithm",
                 "key_lifetime", "region"]
}

ibm_vpn_gateway_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "vpc_id": {"type": "string", "minLength": 1},
        "cloud_id": {"type": "string", "minLength": 1},
        "subnet": {"type": "string", "minLength": 1},
        "resource_group": {"type": "string", "minLength": 1},
        "connections": {
            "type": "array",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "local_cidrs": {"type": "array", "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$"},
                "peer_cidrs": {"type": "array", "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$"},
                "peer_address": {"type": "string", "format": "ipv4"},
                "dead_peer_detection": {
                    "type": "object",
                    "properties": {
                        "interval": {"type": "integer", "minimum": 1, "maximum": 86399},
                        "timeout": {"type": "integer", "minimum": 2, "maximum": 86399},
                         "action": {
                                        "type": "string",
                                        "minLength": 1, "enum": ["clear", "hold", "none", "restart"]
                                    },
                    }
                },
                "pre_shared_secret": {"type": "string", "minLength": 1},
                "ipsec_policy_id": {"type": "string", "minLength": 1},
                "ike_policy_id": {"type": "string", "minLength": 1}
            }
        }
    },
    "required": ["name", "vpc_id", "cloud_id", "subnet"]
}

ibm_vpn_connection_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                 "maxLength": 63},
        "cloud_id": {"type": "string", "minLength": 1},
        "dead_peer_detection": {
            "type": "object",
            "properties": {
                "interval": {"type": "integer", "minimum": 1, "maximum": 86399},
                "timeout": {"type": "integer", "minimum": 2, "maximum": 86399},
                "action": {
                    "type": "string",
                    "minLength": 1, "enum": ["clear", "hold", "none", "restart"]
                },
            }
        },
        "local_cidrs": {"type": "array", "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$"},
        "peer_cidrs": {"type": "array", "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$"},
        "vpn_gateway_id": {"type": "string", "minLength": 1},
        "peer_address": {"type": "string", "format": "ipv4"},
        "pre_shared_secret": {"type": "string", "minLength": 6, "pattern": "^(?=[\-\+\&\!\@\#\$\%\^\*\(\)\,\.\:\_a-zA-Z0-9]{6,128}$)(?:(?!^0[xs]).).*$"},
        "ipsec_policy_id": {"type": "string", "pattern": "^[-0-9a-z_]+$", "minLength": 1},
        "ike_policy_id": {"type": "string", "pattern": "^[-0-9a-z_]+$", "minLength": 1}
    },
    "required": ["name", "cloud_id", "local_cidrs", "peer_cidrs", "pre_shared_secret", "vpn_gateway_id", "peer_address"]
}
