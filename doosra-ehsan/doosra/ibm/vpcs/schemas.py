ibm_vpc_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63,
        },
        "classic_access": {"type": "boolean", "pattern": "^(true|false)$"},
        "resource_group": {"type": "string", "minLength": 1},
        "region": {"type": "string", "minLength": 1},
        "address_prefix_management": {"type": "string", "pattern": "^(auto|manual)$"},
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "is_workspace": {"type": "boolean", "pattern": "^(true|false)$", "default": "false"},
        "address_prefixes": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "is_default": {"type": "boolean", "pattern": "^(true|false)$"},
                    "zone": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "address": {
                        "type": "string",
                        "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                },
                "required": ["zone", "address", "is_default"],
            },
        },
        "public_gateways": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "zone": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                },
                "required": ["name", "zone"],
            },
        },
        "kubernetes_clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",
                        "minLength": 1,
                        "maxLength": 32,
                    },
                    "disable_public_service_endpoint": {"type": "boolean", "pattern": "^(true|false)$"},
                    "kube_version": {"type": "string", "minLength": 1, "maxLength": 18},
                    "pod_subnet": {
                        "type": "string",
                        "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
                    },
                    "service_subnet": {
                        "type": "string",
                        "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
                    },
                    "provider": {"type": "string"},
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                    "worker_pools": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "pattern": "[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",
                                    "minLength": 1,
                                    "maxLength": 32,
                                },
                                "disk_encryption": {"type": "boolean", "pattern": "^(true|false)$"},
                                "flavor": {"type": "string"},
                                "worker_count": {"integer": "string"},
                                "zones": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "zone": {
                                                "type": "string",
                                                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                                "minLength": 1,
                                                "maxLength": 63,
                                            },
                                            "subnets": {
                                                "type": "array",
                                                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                                "minLength": 1,
                                                "maxLength": 63,
                                            },
                                        },
                                        "required": [
                                            "zone",
                                            "subnets"
                                        ]
                                    }
                                }
                            },
                            "required": [
                                "name",
                                "flavor",
                                "disk_encryption",
                                "worker_count",
                                "zones"
                            ]
                        },
                    },
                },
                "required": [
                    "name",
                    "disable_public_service_endpoint",
                    "pod_subnet",
                    "service_subnet",
                    "kube_version",
                    "provider",
                    "worker_pools"
                ]
            },
        },
        "dedicated_hosts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                        "maxLength": 63
                    },
                    "region": {"type": "string", "minLength": 1},
                    "zone": {
                        "type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
                        "maxLength": 63
                    },
                    "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
                    "instance_placement_enabled": {"type": "boolean"},
                    "resource_group": {"type": "string", "minLength": 1},
                    "dedicated_host_profile": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "minLength": 32, "maxLength": 32}
                        },
                        "required": ["id"]
                    },
                    "dedicated_host_group_name": {"type": "string", "minLength": 1},
                },
                "required": ["name", "region", "zone", "cloud_id", "dedicated_host_profile"]
            },
        },
        # "dedicated_host_groups": {
        #     "type": "array",
        #     "items": {
        #         "type": "object",
        #         "properties": {
        #             "name": {
        #                 "type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
        #                 "maxLength": 63
        #             },
        #             "region": {"type": "string", "minLength": 1},
        #             "zone": {
        #                 "type": "string", "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$", "minLength": 1,
        #                 "maxLength": 63
        #             },
        #             "resource_group": {"type": "string", "minLength": 1},
        #             "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        #             "class": {"type": "string", "minLength": 1},
        #             "family": {
        #                 "type": "string", "enum": ["memory", "balanced", "compute"], "default": "balanced",
        #                 "minLength": 1
        #             },
        #         },
        #         "required": ["name", "region", "zone", "cloud_id", "class", "family"]
        #     },
        # },
        "acls": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                    "rules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                    "minLength": 1,
                                    "maxLength": 63,
                                },
                                "action": {
                                    "type": "string",
                                    "pattern": "^(allow|deny)$",
                                },
                                "direction": {
                                    "type": "string",
                                    "pattern": "^(inbound|outbound)$",
                                },
                                "destination": {"type": "string"},
                                "source": {"type": "string"},
                                "protocol": {
                                    "type": "string",
                                    "Enum": ["all", "tcp", "udp"],
                                },
                                "source_port_max": {"type": "integer", "minLength": 1},
                                "source_port_min": {"type": "integer", "minLength": 1},
                                "destination_port_min": {
                                    "type": "integer",
                                    "minLength": 1,
                                },
                                "destination_port_max": {
                                    "type": "integer",
                                    "minLength": 1,
                                },
                                "code": {"type": "string", "minLength": 1},
                                "type": {"type": "string", "minLength": 1},
                            },
                            "required": ["name", "direction", "action", "protocol"],
                        },
                    },
                },
                "required": ["name", "rules"],
            },
        },
        "subnets": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "zone": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "address_prefix": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "ip_cidr_block": {
                        "type": "string",
                        "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
                    },
                    "network_acl": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                "minLength": 1,
                                "maxLength": 63,
                            },
                            "id": {"type": "string", "minLength": 1},
                        },
                    },
                    "public_gateway": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                },
                "required": ["name", "address_prefix", "zone"],
            },
        },
        "security_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                    "rules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "direction": {
                                    "type": "string",
                                    "pattern": "^(inbound|outbound)$",
                                },
                                "protocol": {
                                    "type": "string",
                                    "Enum": ["all", "icmp", "tcp", "udp"],
                                },
                                "address": {"type": "string"},
                                "cidr_block": {
                                    "type": "string",
                                    "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
                                },
                                "security_group": {"type": "string", "minLength": 1},
                                "port_min": {"type": "integer", "minLength": 1},
                                "port_max": {"type": "integer", "minLength": 1},
                                "code": {"type": "integer", "minLength": 1},
                                "type": {"type": "integer", "minLength": 1},
                            },
                            "required": ["direction", "protocol"],
                        },
                    },
                },
                "required": ["name"],
            },
        },
        "ssh_keys": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                    "public_key": {
                        "type": "string", "pattern": "^ssh-rsa([^\/?#]*)([^?#]*)(\?([^#]*))?(#(.*))?$", "minLength": 1
                    },
                },
                "required": ["name", "public_key"],
            },
        },
        "instances": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "zone": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "data_migration": {"type": "boolean", "pattern": "^(true|false)$"},
                    "instance_profile": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "encryption": {
                        "type": "string",
                        "default": "provider_managed",
                        "minLength": 1,
                    },
                    "type": {
                        "type": "string",
                        "enum": ["boot", "data"],
                        "default": "data",
                        "minLength": 1,
                    },
                    "image": {
                        "type": "object",
                        "properties": {
                            "image_location": {"type": "string",
                                               "pattern": "^(classical_vsi|classical_image|cos_vhd|cos_vmdk|cos_qcow2|custom_image|public_image)$"},
                            "classical_account_id": {"type": "string"},
                            "classical_instance_id": {"type": "integer", "minimum": 1},
                            "classical_image_id": {"type": "integer", "minimum": 1},
                            "bucket_name": {"type": "string"},
                            "bucket_object": {"type": "string", "minLength": 1},
                            "image_name": {"type": "string", "minLength": 1},
                            "custom_image": {"type": "string", "minLength": 1},
                            "public_image": {"type": "string", "minLength": 10, "maxLength": 100},
                            "vpc_image_name": {"type": "string", "minLength": 10, "maxLength": 100},
                        },
                        "anyOf": [
                            {"required": ["image_location", "vpc_image_name"]},
                            {"required": ["image_location", "public_image"]},
                            {"required": ["image_location", "custom_image"]}
                        ],
                    },
                    "user_data": {"type": "string", "minLength": 1},
                    "ssh_keys": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                    "minLength": 1,
                                    "maxLength": 63,
                                },
                                "id": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                    "network_interfaces": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "minLength": 1, "maxLength": 63},
                                "subnet": {
                                    "type": "string",
                                    "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                    "minLength": 1,
                                    "maxLength": 63,
                                },
                                "security_groups": {
                                    "type": "array",
                                    "minItems": 1,
                                    "items": {"type": "string"},
                                },
                                "reserve_floating_ip": {
                                    "type": "boolean",
                                    "pattern": "^(true|false)$",
                                },
                                "is_primary": {
                                    "type": "boolean",
                                    "pattern": "^(true|false)$",
                                },
                            },
                            "required": ["name", "subnet", "reserve_floating_ip", "is_primary"],
                        },
                    },
                    "volume_attachments": {
                        "type": "array",
                        "properties": {
                            "volume": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                        "minLength": 1,
                                        "maxLength": 63,
                                    },
                                    "capacity": {
                                        "type": "integer",
                                        "minimum": 10,
                                        "maximum": 2000,
                                    },
                                    "iops": {"type": "integer", "minimum": 1},
                                    "zone": {
                                        "type": "string",
                                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                        "minLength": 1,
                                        "maxLength": 63,
                                    },
                                    "encryption": {
                                        "type": "string",
                                        "enum": ["provider_managed", "user_managed"],
                                        "minLength": 1,
                                    },
                                    "profile": {
                                        "type": "object",
                                        "properties": {
                                            "family": {
                                                "type": "string",
                                                "minLength": 1,
                                            },
                                            "name": {
                                                "type": "string",
                                                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                                "minLength": 1,
                                                "maxLength": 63,
                                            },
                                        },
                                        "required": ["family", "name"],
                                    },
                                },
                                "required": [
                                    "name",
                                    "capacity",
                                    "iops",
                                    "zone",
                                    "encryption",
                                    "profile",
                                ],
                            },
                            "is_delete": {
                                "type": "boolean",
                                "pattern": "^(true|false)$",
                            },
                            "capacity": {"type": "string", "minLength": 1},
                            "volume_profile_type": {"type": "string", "minLength": 1},
                            "volume_index": {"type": "string", "minLength": 1},
                            "name": {
                                "type": "string",
                                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                "minLength": 1,
                                "maxLength": 63,
                            },
                        },
                        "required": ["volume"],
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                    "dedicated_host_id": {"type": "string", "minLength": 1},
                    "dedicated_host_name": {"type": "string", "minLength": 1},
                    "dedicated_host_group_name": {"type": "string", "minLength": 1},
                },
                "required": [
                    "name",
                    "zone",
                    "instance_profile",
                    "image",
                    "network_interfaces",
                    "ssh_keys"
                ],
            },
        },
        "load_balancers": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "is_public": {"type": "boolean", "pattern": "^(true|false)$"},
                    "subnets": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                    "listeners": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "port": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 65535,
                                },
                                "protocol": {
                                    "type": "string",
                                    "enum": ["http", "https", "tcp"],
                                    "minLength": 1,
                                },
                                "connection_limit": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 15000,
                                },
                                "default_pool": {
                                    "type": "string",
                                    "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                    "minLength": 1,
                                    "maxLength": 63,
                                },
                            },
                            "required": ["port", "protocol", "default_pool"],
                        },
                    },
                    "pools": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "minItems": 1,
                            "properties": {
                                "algorithm": {
                                    "type": "string",
                                    "enum": [
                                        "least_connections",
                                        "round_robin",
                                        "weighted_round_robin",
                                    ],
                                    "minLength": 1,
                                },
                                "protocol": {
                                    "type": "string",
                                    "enum": ["http", "tcp"],
                                    "minLength": 1,
                                },
                                "name": {
                                    "type": "string",
                                    "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                                    "minLength": 1,
                                    "maxLength": 63,
                                },
                                "session_persistence": {
                                    "type": "string",
                                    "enum": ["source_ip"],
                                    "minLength": 1,
                                },
                                "health_monitor": {
                                    "type": "object",
                                    "items": {
                                        "type": "object",
                                        "minItems": 1,
                                        "properties": {
                                            "delay": {
                                                "type": "integer",
                                                "minLength": 2,
                                                "maxLength": 60,
                                            },
                                            "max_retries": {
                                                "type": "integer",
                                                "minLength": 2,
                                                "maxLength": 10,
                                            },
                                            "timeout": {
                                                "type": "integer",
                                                "minLength": 2,
                                                "maxLength": 59,
                                            },
                                            "protocol": {
                                                "type": "string",
                                                "enum": ["http", "tcp"],
                                                "minLength": 1,
                                            },
                                            "port": {
                                                "type": "integer",
                                                "minLength": 1,
                                                "maxLength": 65535,
                                            },
                                            "url_path": {
                                                "type": "string",
                                                "minLength": 1,
                                            },
                                        },
                                        "required": [
                                            "delay",
                                            "max_retries",
                                            "timeout",
                                            "protocol",
                                            "url_path",
                                        ],
                                    },
                                },
                                "members": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "minItems": 1,
                                        "properties": {
                                            "port": {
                                                "type": "integer",
                                                "minLength": 1,
                                                "maxLength": 65535,
                                            },
                                            "instance_id": {
                                                "type": "string",
                                                "minLength": 1,
                                            },
                                            "weight": {
                                                "type": "integer",
                                                "minLength": 1,
                                                "maxLength": 100,
                                            },
                                        },
                                        "required": ["port", "instance"],
                                    },
                                },
                                "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                            },
                            "required": [
                                "name",
                                "algorithm",
                                "protocol",
                                "health_monitor",
                            ],
                        },
                    },
                },
                "required": ["name", "subnets", "is_public"],
            },
        },
        "ike_policies": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "authentication_algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"],
                        "minLength": 1,
                    },
                    "dh_group": {"type": "integer", "enum": [2, 5, 14]},
                    "encryption_algorithm": {
                        "type": "string",
                        "enum": ["triple_des", "aes128", "aes256"],
                        "minLength": 1,
                    },
                    "ike_version": {
                        "type": "integer",
                        "enum": [1, 2],
                        "minimum": 1,
                        "maximum": 2,
                    },
                    "key_lifetime": {
                        "type": "integer",
                        "minimum": 1800,
                        "maximum": 86400,
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                },
                "required": [
                    "name",
                    "ike_version",
                    "dh_group",
                    "encryption_algorithm",
                    "key_lifetime",
                    "authentication_algorithm",
                ],
            },
        },
        "ipsec_policies": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "authentication_algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"],
                        "minLength": 1,
                    },
                    "pfs": {
                        "type": "string",
                        "minLength": 1,
                        "pattern": "^(?=[\-\+\&\!\@\#\$\%\^\*\(\)\,\.\:\_a-zA-Z0-9]{6,128}$)(?:(?!^0[xs]).).*$",
                    },
                    "encryption_algorithm": {
                        "type": "string",
                        "enum": ["triple_des", "aes128", "aes256"],
                        "minLength": 1,
                    },
                    "key_lifetime": {
                        "type": "integer",
                        "minimum": 1800,
                        "maximum": 86400,
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                },
                "required": [
                    "name",
                    "encryption_algorithm",
                    "key_lifetime",
                    "authentication_algorithm",
                ],
            },
        },
        "vpns": {
            "type": "array",
            "items": {
                "type": "object",
                "minItems": 1,
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "subnet": {
                        "type": "string",
                        "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                        "minLength": 1,
                        "maxLength": 63,
                    },
                    "connections": {
                        "type": "array",
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "local_cidrs": {
                                "type": "array",
                                "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
                            },
                            "peer_cidrs": {
                                "type": "array",
                                "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
                            },
                            "peer_address": {"type": "string"},
                            "dead_peer_detection": {
                                "type": "object",
                                "properties": {
                                    "interval": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "maximum": 86399,
                                    },
                                    "timeout": {
                                        "type": "integer",
                                        "minimum": 2,
                                        "maximum": 86399,
                                    },
                                    "action": {
                                        "type": "string",
                                        "minLength": 1,
                                        "enum": ["clear", "hold", "none", "restart"],
                                    },
                                },
                            },
                            "pre_shared_secret": {
                                "type": "string",
                                "minLength": 6,
                                "pattern": "^(?=[\-\+\&\!\@\#\$\%\^\*\(\)\,\.\:\_a-zA-Z0-9]{6,128}$)(?:(?!^0[xs]).).*$",
                            },
                            "ipsec_policy": {"type": "string", "minLength": 1},
                            "ike_policy": {"type": "string", "minLength": 1},
                        },
                        "required": ["name", "peer_address", "pre_shared_secret"],
                    },
                    "is_provisioning": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                },
                "required": ["name", "subnet", "connections"],
            },
        },
        "softlayer_cloud_id": {"type": "string", "minLength": 1},
    },
    "routes": {
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "next_hop_address": {"type": "string"},
            "zone": {
                "type": "string",
                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                "minLength": 1,
                "maxLength": 63,
            },
            "name": {
                "type": "string",
                "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
                "minLength": 1,
                "maxLength": 63,
            },
            "required": ["name", "destination", "next_hop_address", "zone"],
        },
    },
    "required": [
        "name",
        "region",
        "address_prefix_management",
        "classic_access",
        "resource_group",
        "cloud_id",
    ],
}

ibm_subnet_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63,
        },
        "zone": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63,
        },
        "ip_cidr_block": {
            "type": "string",
            "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
        },
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "resource_group": {"type": "string", "minLength": 1},
        "public_gateway": {"type": "boolean", "pattern": "^(true|false)$"},
    },
    "required": ["name", "zone", "cloud_id", "ip_cidr_block", "public_gateway", "resource_group"],
}

ibm_attach_subnet_to_public_gateway_schema = {
    "type": "object",
    "properties": {"cloud_id": {"type": "string", "minLength": 32, "maxLength": 32}},
    "required": ["cloud_id"],
}

ibm_attach_subnet_to_acl_schema = {
    "type": "object",
    "properties": {
        "cloud_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "acl_id": {"type": "string", "minLength": 32, "maxLength": 32},
    },
    "required": ["cloud_id", "acl_id"],
}
ibm_vpc_address_prefix = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63,
        },
        "zone": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63,
        },
        "address": {
            "type": "string",
            "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
        },
    },
    "required": ["name", "address"],
}
ibm_routes_schema = {
    "type": "object",
    "properties": {
        "destination": {"type": "string"},
        "next_hop_address": {"type": "string"},
        "zone": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63,
        },
        "name": {
            "type": "string",
            "pattern": "^([a-z]|[a-z][-a-z0-9]*[a-z0-9])$",
            "minLength": 1,
            "maxLength": 63,
        },
    },
    "required": [
        "name",
        "destination",
        "next_hop_address",
        "zone",
    ],
}
