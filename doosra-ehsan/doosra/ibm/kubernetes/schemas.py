ibm_add_kubernetes_cluster_schema={
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "pattern": "[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",
            "minLength": 1,
            "maxLength": 32,
        },
        "type": {"type": "string", "pattern": "^(openshift|kubernetes)$", "default": "kubernetes" },
        "disable_public_service_endpoint": {"type": "boolean", "pattern": "^(true|false)$", "default": "false"},
        "kube_version": {"type": "string", "minLength": 1, "maxLength": 18},
        "region":{
            "type": "string"
        },
        "pod_subnet": {
            "type": ["string", "null"],
            "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
        },
        "provider": {
            "type": "string",
        },
        "service_subnet": {
            "type": ["string", "null"],
            "pattern": "^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d).){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(/([0-9]|[1-2][0-9]|3[0-2]))$",
        },
        "vpc_id": {
            "type": "string"
        },
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
                    "disk_encryption": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
                    "flavor": {
                        "type": "string",
                    },
                    "worker_count": {"type": "string"},
                    "zones": {
                        "type": "array",
                        "items": {
                            "type": "object",
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
                            },
                            "required": [
                                "name",
                                "subnet"
                            ]
                        }
                    }
                },
                "required":[
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
        "type",
        "kube_version",
        "provider",
        "vpc_id",
        "worker_pools"
    ]
}

ibm_add_kubernetes_cluster_workerpool_schema = {
    "type": "object",
    "minItems": 1,
    "properties": {
        "name": {
            "type": "string",
            "pattern": "[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",
            "minLength": 1,
            "maxLength": 32,
        },
        "disk_encryption": {"type": "boolean", "pattern": "^(true|false)$", "default": "true"},
        "flavor": {
            "type": "string",
        },
        "worker_count": {"type": "string"},
        "zones": {
            "type": "array",
            "items": {
                "type": "object",
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
                },
                "required": [
                    "name",
                    "subnet"
                ]
            }
        }
    },
    "required":[
        "name",
        "flavor",
        "disk_encryption",
        "worker_count",
        "zones"
    ]
}