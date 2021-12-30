"""
Utils for Dedicated Hosts
"""
import logging
import time

from doosra import db as doosradb
from doosra.common.clients.ibm_clients import DedicatedHostsClient, InstancesClient, ResourceGroupsClient
from doosra.common.clients.ibm_clients.exceptions import IBMAuthError, IBMInvalidRequestError, IBMExecuteError, \
    IBMConnectError
from doosra.ibm.clouds.consts import INVALID
from doosra.models import IBMCloud, IBMDedicatedHost, IBMDedicatedHostGroup, IBMDedicatedHostProfile, \
    IBMInstanceProfile, IBMResourceGroup, WorkSpace
from doosra.tasks.exceptions import TaskFailureError

LOGGER = logging.getLogger(__name__)


def configure_dedicated_host(data, workspace_id=None):
    """
    Function containing the code to create an IBM Dedicated Host on IBM cloud
    :param data: <dict> JSON for Dedicated Host creation
    :raises TaskFailureError
    :return:
    """
    ibm_cloud = doosradb.session.query(IBMCloud).get(data["cloud_id"])
    if not ibm_cloud:
        LOGGER.debug("IBM cloud with ID {} not found".format(data["cloud_id"]))
        raise TaskFailureError(f"IBM cloud with ID {data['cloud_id']} not found")

    json_data = {}
    if data.get("name"):
        json_data["name"] = data["name"]

    if "instance_placement_enabled" in data and not data["instance_placement_enabled"]:
        json_data["instance_placement_enabled"] = data["instance_placement_enabled"]

    if data.get("resource_group"):
        dh_resource_group = ibm_cloud.resource_groups.filter_by(name=data["resource_group"]).first()
        if not dh_resource_group:
            raise TaskFailureError(f"Resource Group {data['resource_group']} not found")

        json_data["resource_group"] = {
            "id": dh_resource_group.resource_id
        }

    dh_profile = \
        ibm_cloud.dedicated_host_profiles.filter_by(
            id=data["dedicated_host_profile"]["id"], region=data["region"]
        ).first()
    if not dh_profile:
        raise TaskFailureError(f"Dedicated host profile with ID {data['dedicated_host_profile']['id']} not found")

    json_data["profile"] = {
        "name": dh_profile.name
    }

    if data.get("dedicated_host_group_name"):
        dh_group = \
            ibm_cloud.dedicated_host_groups.filter_by(
                name=data["dedicated_host_group_name"], region=data["region"]
            ).first()
        if not dh_group:
            raise TaskFailureError(
                f"Dedicated host group '{data['dedicated_host_group_name']}' not found in region {data['region']}"
            )

        json_data["group"] = {
            "id": dh_group.resource_id
        }
    else:
        json_data["zone"] = {
            "name": data["zone"]
        }
        if data.get("dedicated_host_group"):
            if data["dedicated_host_group"].get("name"):
                json_data["group"] = {
                    "name": data["dedicated_host_group"]["name"]
                }

            if data["dedicated_host_group"].get("resource_group"):
                dh_group_resource_group = \
                    ibm_cloud.resource_groups.filter_by(name=data["dedicated_host_group"]["resource_group"]).first()
                if not dh_group_resource_group:
                    raise TaskFailureError(
                        f"Resource Group {data['dedicated_host_group']['resource_group']} not found"
                    )

                json_data["group"] = json_data.get("group") or {}
                json_data["group"]["resource_group"] = {
                    "id": dh_group_resource_group.resource_id
                }

    LOGGER.info(f"Creating IBM Dedicated Host '{data['name']}' on IBM Cloud")
    try:
        dh_client = DedicatedHostsClient(cloud_id=data["cloud_id"])
        new_dedicated_host = dh_client.create_dedicated_host(region=data["region"], dedicated_host_json=json_data)
        retries = 6
        while new_dedicated_host["lifecycle_state"] != "stable" and new_dedicated_host["state"] != "available":

            if new_dedicated_host["lifecycle_state"] == "failed":
                raise TaskFailureError(f"Dedicated Host with name {new_dedicated_host.get('name')} FAILED Provisioning")

            if not retries:
                raise TaskFailureError(
                    "Request for Dedicated Host Creation accepted by IBM but could not get 'stable' state within 30 "
                    "seconds"
                )

            retries -= 1
            time.sleep(5)
            new_dedicated_host = \
                dh_client.get_dedicated_host(region=data["region"], dedicated_host_id=new_dedicated_host["id"])

        dedicated_host = IBMDedicatedHost.from_ibm_json(new_dedicated_host)
        dedicated_host.cloud_id = ibm_cloud.id

        dh_resource_group = \
            ibm_cloud.resource_groups.filter_by(resource_id=new_dedicated_host["resource_group"]["id"]).first()
        if not dh_resource_group:
            rg_client = ResourceGroupsClient(cloud_id=data["cloud_id"])
            dh_resource_group_json = rg_client.get_resource_group(new_dedicated_host["resource_group"]["id"])
            dh_resource_group = IBMResourceGroup.from_ibm_json_body(dh_resource_group_json)
            dh_resource_group.cloud_id = data["cloud_id"]
            doosradb.session.add(dh_resource_group)
            doosradb.session.commit()

        dedicated_host.resource_group_id = dh_resource_group.id

        dh_group = \
            ibm_cloud.dedicated_host_groups.filter_by(
                resource_id=new_dedicated_host["group"]["id"], region=data["region"]
            ).first()
        if not dh_group:
            dh_group_json = \
                dh_client.get_dedicated_host_group(
                    region=data["region"], dedicated_host_group_id=new_dedicated_host["group"]["id"]
                )
            dh_group = IBMDedicatedHostGroup.from_ibm_json(dh_group_json)
            dh_group.cloud_id = ibm_cloud.id

            dh_group_resource_group = \
                ibm_cloud.resource_groups.filter_by(resource_id=dh_group_json["resource_group"]["id"]).first()
            if not dh_group_resource_group:
                rg_client = ResourceGroupsClient(cloud_id=data["cloud_id"])
                dh_group_resource_group_json = rg_client.get_resource_group(dh_group_json["resource_group"]["id"])
                dh_group_resource_group = IBMResourceGroup.from_ibm_json_body(dh_group_resource_group_json)
                dh_group_resource_group.cloud_id = data["cloud_id"]
                doosradb.session.add(dh_group_resource_group)
                doosradb.session.commit()

            dh_group.resource_group_id = dh_group_resource_group.id
            doosradb.session.add(dh_group)
            doosradb.session.commit()

            for supported_instance_profile in dh_group_json["supported_instance_profiles"]:
                instance_profile_obj = \
                    ibm_cloud.instance_profiles.filter_by(name=supported_instance_profile["name"]).first()
                if not instance_profile_obj:
                    instances_client = InstancesClient(data["cloud_id"])
                    instance_profile_json = \
                        instances_client.get_instance_profile(dedicated_host.region, supported_instance_profile["name"])
                    instance_profile_obj = IBMInstanceProfile.from_ibm_json_body(instance_profile_json)
                    instance_profile_obj.cloud_id = data["cloud_id"]
                    doosradb.session.add(instance_profile_obj)
                    doosradb.session.commit()

                dh_group.supported_instance_profiles.append(instance_profile_obj)

        dedicated_host.dedicated_host_group_id = dh_group.id

        dh_profile = \
            ibm_cloud.dedicated_host_profiles.filter_by(
                region=dedicated_host.region, name=new_dedicated_host["profile"]["name"]
            ).first()
        if not dh_profile:
            dh_profile_json = dh_client.get_dedicated_host_profile(
                dedicated_host.region, new_dedicated_host["profile"]["name"]
            )
            dh_profile = IBMDedicatedHostProfile.from_ibm_json(dh_profile_json)
            dh_profile.cloud_id = data["cloud_id"]
            doosradb.session.add(dh_profile)
            doosradb.session.commit()

        dedicated_host.dedicated_host_profile_id = dh_profile.id

        for supported_instance_profile in new_dedicated_host["supported_instance_profiles"]:
            instance_profile_obj = \
                ibm_cloud.instance_profiles.filter_by(name=supported_instance_profile["name"]).first()
            if not instance_profile_obj:
                instances_client = InstancesClient(data["cloud_id"])
                instance_profile_json = \
                    instances_client.get_instance_profile(dedicated_host.region, supported_instance_profile["name"])
                instance_profile_obj = IBMInstanceProfile.from_ibm_json_body(instance_profile_json)
                instance_profile_obj.cloud_id = data["cloud_id"]
                doosradb.session.add(instance_profile_obj)
                doosradb.session.commit()

            dedicated_host.supported_instance_profiles.append(instance_profile_obj)

        doosradb.session.add(dedicated_host)
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        LOGGER.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
        doosradb.session.commit()

        workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
        if not workspace:
            raise

        new_metadata = workspace.request_metadata
        if "dedicated_hosts" not in new_metadata:
            new_metadata["dedicated_hosts"] = []

        new_metadata["dedicated_hosts"].append(data)

        workspace.request_metadata = new_metadata
        doosradb.session.commit()

        raise TaskFailureError(str(ex))

    workspace = doosradb.session.query(WorkSpace).filter_by(id=workspace_id).first()
    if not workspace:
        return dedicated_host
    new_req_metadata = workspace.request_metadata

    if "provisioned_dedicated_host_ids" not in new_req_metadata:
        new_req_metadata["provisioned_dedicated_host_ids"] = []
    new_req_metadata["provisioned_dedicated_host_ids"].append(dedicated_host.id)
    workspace.request_metadata = new_req_metadata
    doosradb.session.commit()

    return dedicated_host


def delete_dedicated_host(cloud_id, dedicated_host_id):
    """
    Function containing the code to delete an IBM Dedicated Host from IBM cloud
    :param cloud_id: <string> ID of the cloud in doosradb
    :param dedicated_host_id: <string> ID of the Dedicated Host on IBM Cloud
    :raises TaskFailureError
    :return:
    """
    from doosra.common.clients.ibm_clients import DedicatedHostsClient

    ibm_cloud = doosradb.session.query(IBMCloud).get(cloud_id)
    if not ibm_cloud:
        error = f"IBM cloud with ID {cloud_id} not found"
        LOGGER.debug(error)
        raise TaskFailureError(error)

    dedicated_host = ibm_cloud.dedicated_hosts.filter_by(id=dedicated_host_id).first()
    if not dedicated_host:
        error = f"Dedicated host with ID {dedicated_host_id} not found"
        LOGGER.debug(error)
        raise TaskFailureError(error)

    dh_client = DedicatedHostsClient(cloud_id)
    if dedicated_host.instance_placement_enabled:
        try:
            dh_client.update_dedicated_host(
                dedicated_host.region, dedicated_host_id=dedicated_host.resource_id,
                updated_dh_json={"instance_placement_enabled": False}
            )
        except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
            LOGGER.debug(ex)
            if isinstance(ex, IBMExecuteError) and ex.error_code == 404:
                doosradb.session.delete(dedicated_host)
                doosradb.session.commit()
                return

            if isinstance(ex, IBMAuthError):
                ibm_cloud.status = INVALID
            doosradb.session.commit()

    try:
        dh_client.delete_dedicated_host(region=dedicated_host.region, dedicated_host_id=dedicated_host.resource_id)
        doosradb.session.delete(dedicated_host)
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        LOGGER.info(ex)
        if isinstance(ex, IBMExecuteError) and ex.error_code == 404:
            doosradb.session.delete(dedicated_host)
            doosradb.session.commit()
            return

        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
        doosradb.session.commit()
        raise TaskFailureError(str(ex))


def configure_dedicated_host_group(data):
    """
    Function containing the code to create an IBM Dedicated Host Group on IBM cloud
    :param data: <dict> JSON for Dedicated Host Group creation
    :raises TaskFailureError
    :return:
    """
    ibm_cloud = doosradb.session.query(IBMCloud).get(data["cloud_id"])
    if not ibm_cloud:
        error = "IBM cloud with ID {} not found".format(data["cloud_id"])
        LOGGER.debug(error)
        raise TaskFailureError(error)

    json_data = {
        "class": data["class"],
        "family": data["family"],
    }
    if data.get("name"):
        json_data["name"] = data["name"]

    if data.get("resource_group"):
        dh_group_resource_group = ibm_cloud.resource_groups.filter_by(name=data["resource_group"]).first()
        if not dh_group_resource_group:
            raise TaskFailureError(f"Resource Group {data['resource_group']} not found")

        json_data["resource_group"] = {
            "id": dh_group_resource_group.resource_id
        }

    json_data["zone"] = {
        "name": data["zone"]
    }

    LOGGER.info(f"Creating IBM Dedicated Host Group '{data['name']}' on IBM Cloud")
    try:
        dh_client = DedicatedHostsClient(cloud_id=data["cloud_id"])
        new_dedicated_host_group = \
            dh_client.create_dedicated_host_group(region=data["region"], dedicated_host_group_json=json_data)

        dedicated_host_group = IBMDedicatedHostGroup.from_ibm_json(new_dedicated_host_group)
        dedicated_host_group.cloud_id = ibm_cloud.id

        dh_group_resource_group = \
            ibm_cloud.resource_groups.filter_by(resource_id=new_dedicated_host_group["resource_group"]["id"]).first()
        if not dh_group_resource_group:
            rg_client = ResourceGroupsClient(cloud_id=data["cloud_id"])
            dh_group_resource_group_json = \
                rg_client.get_resource_group(new_dedicated_host_group["resource_group"]["id"])
            dh_group_resource_group = IBMResourceGroup.from_ibm_json_body(dh_group_resource_group_json)
            dh_group_resource_group.cloud_id = data["cloud_id"]
            doosradb.session.add(dh_group_resource_group)
            doosradb.session.commit()

        dedicated_host_group.resource_group_id = dh_group_resource_group.id

        for supported_instance_profile in new_dedicated_host_group["supported_instance_profiles"]:
            instance_profile_obj = \
                ibm_cloud.instance_profiles.filter_by(name=supported_instance_profile["name"]).first()
            if not instance_profile_obj:
                instances_client = InstancesClient(data["cloud_id"])
                instance_profile_json = \
                    instances_client.get_instance_profile(
                        dedicated_host_group.region, supported_instance_profile["name"]
                    )
                instance_profile_obj = IBMInstanceProfile.from_ibm_json_body(instance_profile_json)
                instance_profile_obj.cloud_id = data["cloud_id"]
                doosradb.session.add(instance_profile_obj)
                doosradb.session.commit()

            dedicated_host_group.supported_instance_profiles.append(instance_profile_obj)

        doosradb.session.add(dedicated_host_group)
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        LOGGER.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
        doosradb.session.commit()
        raise TaskFailureError(str(ex))

    return dedicated_host_group


def delete_dedicated_host_group(cloud_id, dedicated_host_group_id):
    """
    Function containing the code to delete an IBM Dedicated Host Group from IBM cloud
    :param cloud_id: <string> ID of the cloud in doosradb
    :param dedicated_host_group_id: <string> ID of the Dedicated Host Group on IBM Cloud
    :raises TaskFailureError
    :return:
    """
    from doosra.common.clients.ibm_clients import DedicatedHostsClient

    ibm_cloud = doosradb.session.query(IBMCloud).get(cloud_id)
    if not ibm_cloud:
        error = f"IBM cloud with ID {cloud_id} not found"
        LOGGER.debug(error)
        raise TaskFailureError(error)

    dedicated_host_group = ibm_cloud.dedicated_host_groups.filter_by(id=dedicated_host_group_id).first()
    if not dedicated_host_group:
        error = f"Dedicated host with ID {dedicated_host_group_id} not found"
        LOGGER.debug(error)
        raise TaskFailureError(error)

    try:
        dh_client = DedicatedHostsClient(cloud_id)
        dh_client.delete_dedicated_host_group(
            region=dedicated_host_group.region, dedicated_host_group_id=dedicated_host_group.resource_id
        )
        doosradb.session.delete(dedicated_host_group)
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        LOGGER.info(ex)
        if isinstance(ex, IBMExecuteError) and ex.error_code == 404:
            doosradb.session.delete(dedicated_host_group)
            doosradb.session.commit()
            return

        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
        doosradb.session.commit()
        raise TaskFailureError(str(ex))


def sync_dedicated_host_profiles(cloud_id, region):
    """
    Sync IBM Dedicated Host Profiles from IBM Cloud and store them in DB
    :param cloud_id: <string> ID of the cloud in doosradb
    :param region: <string> Region of the IBM Cloud
    :raises TaskFailureError
    :return:
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id).first()
    if not ibm_cloud:
        error = f"IBM Cloud {cloud_id} Deleted"
        LOGGER.error(error)
        raise TaskFailureError(error)

    try:
        dh_client = DedicatedHostsClient(cloud_id)
        dedicated_host_profile_jsons = dh_client.list_dedicated_host_profiles(region=region)
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        LOGGER.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
        raise TaskFailureError(str(ex))

    for dedicated_host_profile_json in dedicated_host_profile_jsons:
        updated_dedicated_host_profile = IBMDedicatedHostProfile.from_ibm_json(dedicated_host_profile_json)
        updated_supported_instance_profiles = list()
        for supported_instance_profile_json in dedicated_host_profile_json["supported_instance_profiles"]:
            instance_profile_obj = \
                ibm_cloud.instance_profiles.filter_by(name=supported_instance_profile_json["name"]).first()
            if not instance_profile_obj:
                instances_client = InstancesClient(cloud_id)
                instance_profile_json = \
                    instances_client.get_instance_profile(region, supported_instance_profile_json["name"])
                instance_profile_obj = IBMInstanceProfile.from_ibm_json_body(instance_profile_json)
                instance_profile_obj.cloud_id = cloud_id
                doosradb.session.add(instance_profile_obj)
                doosradb.session.commit()

            updated_supported_instance_profiles.append(instance_profile_obj)

        existing_dedicated_host_profile = \
            doosradb.session.query(IBMDedicatedHostProfile).filter_by(
                cloud_id=cloud_id, name=updated_dedicated_host_profile.name, region=region
            ).first()
        if existing_dedicated_host_profile:
            existing_dedicated_host_profile.update_from_obj(
                updated_dedicated_host_profile, updated_supported_instance_profiles
            )
        else:
            updated_dedicated_host_profile.ibm_cloud = ibm_cloud
            doosradb.session.add(updated_dedicated_host_profile)
            doosradb.session.commit()

            for updated_supported_instance_profile in updated_supported_instance_profiles:
                updated_dedicated_host_profile.supported_instance_profiles.append(
                    updated_supported_instance_profile
                )
        doosradb.session.commit()
