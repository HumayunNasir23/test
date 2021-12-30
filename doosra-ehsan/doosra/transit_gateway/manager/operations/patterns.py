# ***********************
#   CREATE PATTERNS
# ***********************

CREATE_TRANSIT_GATEWAY_PATTERN = [
    "POST", "{{base_url}}/v1/transit_gateways?version={{version}}"
]

CREATE_TRANSIT_GATEWAY_CONNECTION_PATTERN = [
    "POST", "{{base_url}}/v1/transit_gateways/{transit_gateway_id}/connections?version={{version}}"
]

# ***********************
#   GET PATTERNS
# ***********************

GET_RESOURCE_GROUP_PATTERN = [
    "GET", "https://resource-controller.cloud.ibm.com/v2/resource_groups"
]

GET_TRANSIT_GATEWAY_PATTERN = [
    "GET", "{{base_url}}/v1/transit_gateways/{gateway_id}?version={{version}}"
]

GET_TRANSIT_GATEWAY_CONNECTIONS_PATTERN = [
    "GET", "{{base_url}}/v1/transit_gateways/{gateway_id}/connections?version={{version}}"
]

GET_TRANSIT_GATEWAY_CONNECTION_PATTERN = [
    "GET",
    "{{base_url}}/v1/transit_gateways/{gateway_id}/connections/{connection_id}?version={{version}}"
]

# ***********************
#   LIST PATTERNS
# ***********************

LIST_TRANSIT_GATEWAYS_PATTERN = [
    "GET", "{{base_url}}/v1/transit_gateways?version={{version}}"
]

LIST_TRANSIT_GATEWAY_CONNECTIONS_PATTERN = [
    "GET", "{{base_url}}/v1/transit_gateways/{transit_gateway_id}/connections?version={{version}}"
]

LIST_TRANSIT_LOCATIONS = [
    "GET", "{{base_url}}/v1/locations?version={{version}}"
]

# ***********************
#   UPDATE PATTERNS
# ***********************

UPDATE_TRANSIT_GATEWAY_PATTERN = [
    "PATCH", "{{base_url}}/v1/transit_gateways/{gateway_id}?version={{version}}"
]

UPDATE_TRANSIT_GATEWAY_CONNECTION_PATTERN = [
    "PATCH", "{{base_url}}/v1/transit_gateways/{gateway_id}/connections/{connection_id}?version={{version}}"
]

# ***********************
#   DELETE PATTERNS
# ***********************


DELETE_TRANSIT_GATEWAY_PATTERN = [
    "DELETE", "{{base_url}}/v1/transit_gateways/{gateway_id}?version={{version}}"
]

DELETE_TRANSIT_GATEWAY_CONNECTION_PATTERN = [
    "DELETE", "{{base_url}}/v1/transit_gateways/{gateway_id}/connections/{connection_id}?version={{version}}"
]
