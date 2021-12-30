from typing import List, Dict, AnyStr


def get_auto_scale_group(instance) -> AnyStr:
    """
    Get Instance's Auto Group
    @param instance:
    @return:
    """
    if instance.get('scaleMember') and instance['scaleMember'].get('scaleGroup'):
        return instance['scaleMember']['scaleGroup'].get('name')


def list_network_attached_storages(allowed_network_storages: List) -> List[Dict]:
    storage_list = []
    for network_storage in allowed_network_storages:
        storage_list.append({
            "type": network_storage['storageType'].get('keyName'),
            "username": network_storage['username'],
            "capacityGB": network_storage['capacityGb']
        })

    return storage_list
