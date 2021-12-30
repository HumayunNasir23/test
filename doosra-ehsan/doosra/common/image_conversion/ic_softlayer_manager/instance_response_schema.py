instance_response_schema = {
    "type": "object",
    "properties": {
        "status": {
            "type": "object",
            "properties": {
                "keyName": {"type": "string"}
            },
            "required": ["keyName"]
        },
        "powerState": {
            "type": "object",
            "properties": {
                "keyName": {"type": "string"}
            },
            "required": ["keyName"]
        },
        "primaryIpAddress": {"type": "string", "minLength": 1},
        "operatingSystem": {
            "type": "object",
            "properties": {
                "passwords": {"type": "array", "minItems": 1}
            },
            "required": ["passwords"]
        },
    },
    "required": ["status", "powerState", "primaryIpAddress", "operatingSystem"]
}
