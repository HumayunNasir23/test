import logging
import json

from datetime import datetime
from celery import chain, group, Task
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from doosra import db as doosradb
from doosra.ibm.discovery.ibm_dc import (
    IBMAuthError,
    IBMConnectError,
    IBMExecuteError,
    IBMInvalidRequestError,
)
from doosra.common.utils import validate_ip_in_range
from doosra.ibm.managers.operations.rias.consts import (AVAILABLE, ACTIVE, ATTACHED, FAILED, RUNNING, STABLE, PENDING,
                                                        DEPRECATED, CREATE_PENDING, DELETE_PENDING, MAINTENANCE_PENDING,
                                                        UPDATE_PENDING, PAUSED, PAUSING, RESTARTING, RESUMING, STOPPING,
                                                        STARTING, STOPPED, NORMAL, DEPLOYING, WARNING, CLUSTER_DELETED,
                                                        UPDATING, CRITICAL, REQUESTED)
from doosra.ibm.managers.operations.rias.consts import DELETING as IBM_DELETING
from doosra.ibm.managers import IBMManager
from doosra.common.clients.ibm_clients import K8sClient
from doosra.common.clients.ibm_clients.kubernetes.utils import K8s
from doosra.models import (
    IBMCloud,
    IBMResourceGroup,
    IBMNetworkAcl,
    IBMNetworkAclRule,
    IBMFloatingIP,
    IBMSshKey,
    IBMIKEPolicy,
    IBMIPSecPolicy,
    IBMVolumeProfile,
    IBMInstanceProfile,
    IBMImage,
    IBMOperatingSystem,
    IBMSubnet,
    IBMVolume,
    IBMVpcNetwork,
    IBMSecurityGroup,
    IBMSecurityGroupRule,
    IBMPublicGateway,
    IBMAddressPrefix,
    IBMVpnGateway,
    IBMVpnConnection,
    IBMLoadBalancer,
    IBMPool,
    IBMHealthCheck,
    IBMListener,
    IBMInstance,
    IBMVolumeAttachment,
    IBMNetworkInterface,
    IBMPoolMember,
    TransitGateway,
    TransitGatewayConnection,
    WorkSpace,
    IBMDedicatedHost,
    IBMDedicatedHostGroup,
    IBMDedicatedHostProfile,
    KubernetesCluster,
    KubernetesClusterWorkerPool,
    KubernetesClusterWorkerPoolZone,
)

from doosra.models.ibm.instance_models import ibm_network_interfaces_security_groups
from doosra.tasks.celery_app import celery, app
from doosra.common.consts import (
    CREATED,
    CREATING,
    ERROR_CREATING,
    FAILED,
    IN_PROGRESS,
    VALID,
    DELETING,
    DELETED,
    ERROR_DELETING,
    CREATION_PENDING
)
from doosra.tasks.exceptions import WorkflowTerminated

LOGGER = logging.getLogger("discovery_tasks.py")


class BaseSyncTask(Task):
    throws = (
        # Register all expected and handled exceptions here
        IBMAuthError,
        IBMConnectError,
        IBMExecuteError,
        IBMInvalidRequestError,
    )

    queue = "beat_queue"
    ignore_result = True

    def __call__(self, *args, **kwargs):
        with app.app_context():
            custom_task_id = gen_task_id(self.name, kwargs)
            try:
                task_status = celery.backend.get(custom_task_id)
                if task_status:
                    return
                celery.backend.set(custom_task_id, self.request.id)
                if kwargs["identifier_args"].get("group_id"):
                    cloud = doosradb.session.query(IBMCloud).filter_by(
                        group_id=kwargs["identifier_args"].get("group_id")).first()
                else:
                    cloud = doosradb.session.query(IBMCloud).filter_by(
                        id=kwargs["identifier_args"].get("cloud_id")).first()

                region = kwargs["identifier_args"].get("region")

                if not cloud:
                    raise WorkflowTerminated("Cloud not found")
                ibm_manager = (
                    IBMManager(cloud=cloud, region=region, initialize_tg_manager=True)
                    if region
                    else IBMManager(cloud=cloud, initialize_tg_manager=True)
                )
                kwargs['ibm_manager'] = ibm_manager
                result = self.run(*args, **kwargs)
                celery.backend.delete(custom_task_id)
                return result
            except (
                    IBMAuthError,
                    IBMConnectError,
                    IBMExecuteError,
                    IBMInvalidRequestError,
                    WorkflowTerminated
            ) as ex:
                self.request.chain = self.request.callbacks = self.request.group = None
                LOGGER.info("{}".format(ex))
            except (IntegrityError, StaleDataError) as ex:
                # Ignore after effects of integrity error
                LOGGER.info("Exception is: {}".format(ex))
            finally:
                celery.backend.delete(custom_task_id)


def gen_task_id(name, idf_args):
    """create custom task id by combining task name and agrs"""

    custom_task_id = "discovery-{}".format(name)
    for id_ in idf_args["identifier_args"].values():
        custom_task_id += "-{}".format(id_)
    return custom_task_id


def filter_in_progress_tasks(tasks):
    """Filter tasks that are already in progress"""

    filtered_tasks = []
    for task in tasks:
        custom_task_id = gen_task_id(task.name, task.kwargs)
        task_status = celery.backend.get(custom_task_id)
        if task_status:
            logging.info("Task '{}' already running".format(custom_task_id))
            continue
        filtered_tasks.append(task)
    return filtered_tasks


@celery.task(name="initiate_sync", queue="beat_queue", ignore_result=True)
def load_all_clouds():
    """Fetch all clouds"""
    LOGGER.info("Discovery initiated, Loading all Clouds")

    grouped_clouds = doosradb.session.query(IBMCloud.group_id).distinct().filter_by(status=VALID).all()

    for group_ in grouped_clouds:
        group_tasks = [
            sync_resource_group.si(identifier_args={"group_id": group_[0]}),
            sync_instance_profiles.si(identifier_args={"group_id": group_[0]}),
            fetch_regions.si(identifier_args={"group_id": group_[0]})
        ]
        group_tasks = filter_in_progress_tasks(group_tasks)
        if group_tasks:
            chain(
                group_tasks
            ).delay()
            LOGGER.info("--------------- discovery initiated for group {} ---------------".format(group_[0]))


@celery.task(name="fetch_regions", bind=True, base=BaseSyncTask)
def fetch_regions(self, identifier_args, ibm_manager=None):
    """Fetch all regions"""
    group_id = identifier_args["group_id"]
    cloud = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).first()
    LOGGER.info(" --------------------- Fetching all regions of cloud '{}' ------------------------".format(cloud.id))
    regions = ibm_manager.rias_ops.fetch_ops.get_regions()
    cloud_sync_tasks = []
    vpc_sync_tasks = []
    vpc_independent_tasks = []
    dedicated_host_tasks = []
    for region in regions:
        cloud_sync_tasks.append(
            sync_floating_ips.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        cloud_sync_tasks.append(
            sync_ssh_keys.si(identifier_args={"group_id": group_id, "region": region})
        )
        cloud_sync_tasks.append(
            sync_ike_policies.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        cloud_sync_tasks.append(
            sync_ipsec_policies.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        cloud_sync_tasks.append(
            sync_volume_profiles_by_region.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        cloud_sync_tasks.append(
            sync_images_by_region.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        cloud_sync_tasks.append(
            sync_operating_systems.si(identifier_args={"group_id": group_id})
        )
        vpc_sync_tasks.append(
            sync_vpcs.si(identifier_args={"group_id": group_id, "region": region})
        )
        vpc_sync_tasks.append(
            sync_subnets.si(identifier_args={"group_id": group_id, "region": region})
        )
        vpc_independent_tasks.append(
            sync_k8s_clusters.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        vpc_independent_tasks.append(
            sync_k8s_cluster_workloads.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        vpc_independent_tasks.append(
            sync_security_groups.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        vpc_independent_tasks.append(
            sync_acls.si(identifier_args={"group_id": group_id, "region": region})
        )
        vpc_independent_tasks.append(
            sync_public_gateways.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        vpc_independent_tasks.append(
            sync_instances.si(identifier_args={"group_id": group_id, "region": region})
        )
        vpc_independent_tasks.append(
            sync_vpn_gateways.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        vpc_independent_tasks.append(
            sync_transit_gateways.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        vpc_independent_tasks.append(
            sync_load_balancers.si(
                identifier_args={"group_id": group_id, "region": region}
            )
        )
        vpc_independent_tasks.append(sync_volumes.si(identifier_args={"group_id": group_id, "region": region}))
        dedicated_host_tasks.append(
            sync_dedicated_hosts.si(identifier_args={"group_id": group_id, "region": region})
        )
    cloud_sync_tasks = filter_in_progress_tasks(cloud_sync_tasks)
    vpc_sync_tasks = filter_in_progress_tasks(vpc_sync_tasks)
    vpc_independent_tasks = filter_in_progress_tasks(vpc_independent_tasks)
    dedicated_host_tasks = filter_in_progress_tasks(dedicated_host_tasks)
    if cloud_sync_tasks and vpc_sync_tasks and vpc_independent_tasks:
        chain(
            group(cloud_sync_tasks), group(vpc_sync_tasks), group(vpc_independent_tasks), group(dedicated_host_tasks)
        ).delay()


@celery.task(name="sync_resource_groups_by_cloud", bind=True, base=BaseSyncTask)
def sync_resource_group(self, identifier_args, ibm_manager=None):
    """Sync all Resource Groups"""
    LOGGER.info("Discovering all the resource groups")
    group_id = identifier_args["group_id"]
    fetched_objs = ibm_manager.resource_ops.raw_fetch_ops.get_resource_groups()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        names = [obj["name"] for obj in fetched_objs]
        if len(names) != len(set(names)):
            cloud.status = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
            doosradb.session.commit()
            raise IBMInvalidRequestError("Duplicate resource group names")

        cloud.status = VALID
        doosradb.session.commit()

        created_objs = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        id_index = set()
        for obj in fetched_objs:
            id_index.add(obj["id"])

        for obj in created_objs:
            if obj.resource_id not in id_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()

        del id_index
        created_objs = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        id_index = {obj.resource_id: obj for obj in created_objs}
        del created_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
            except KeyError:
                new_obj = IBMResourceGroup(
                    name=obj["name"], resource_id=obj["id"], cloud_id=cloud.id
                )
                doosradb.session.add(new_obj)
        doosradb.session.commit()


@celery.task(name="sync_acls", bind=True, base=BaseSyncTask)
def sync_acls(self, identifier_args, ibm_manager=None):
    """Sync all acls in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info("Syncing acls for group '{}' and region '{}".format(group_id, region))
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_networks_acls()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        rules_tasks = []
        created_or_deleted_objs = (doosradb.session.query(IBMNetworkAcl).filter(
            IBMNetworkAcl.cloud_id == cloud.id, IBMNetworkAcl.region == region,
            IBMNetworkAcl.status.in_([CREATED, DELETED])
        ).all())

        id_index = set()
        for obj in fetched_objs:
            id_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in id_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()

        del id_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMNetworkAcl)
                .filter_by(
                cloud_id=cloud.id, region=region, status=CREATED
            )
                .all()
        )
        failed_objs = (
            doosradb.session.query(IBMNetworkAcl)
                .filter(
                IBMNetworkAcl.cloud_id == cloud.id,
                IBMNetworkAcl.region == region,
                IBMNetworkAcl.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )
        id_index = {acl.resource_id: acl for acl in created_objs}
        name_index = {acl.name: acl for acl in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                rules_tasks.append(
                    sync_acl_rules.si(
                        identifier_args={
                            "cloud_id": cloud.id,
                            "region": region,
                            "acl_id": existing_obj.id,
                        },
                        fetched_objs=obj["rules"],
                    )
                )
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    existing_obj.status = CREATED
                    rules_tasks.append(
                        sync_acl_rules.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "acl_id": existing_obj.id,
                            },
                            fetched_objs=obj["rules"],
                        )
                    )
                else:
                    new_obj = IBMNetworkAcl(
                        name=obj["name"],
                        region=region,
                        resource_id=obj["id"],
                        cloud_id=cloud.id,
                        status=CREATED,
                    )
                    existing_vpc = (
                        doosradb.session.query(IBMVpcNetwork)
                            .filter_by(cloud_id=cloud.id, resource_id=obj['vpc_id'], region=region)
                            .first()
                    )
                    if not existing_vpc:
                        continue
                    new_obj.vpc_id = existing_vpc.id
                    doosradb.session.add(new_obj)
                    rules_tasks.append(
                        sync_acl_rules.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "acl_id": new_obj.id,
                            },
                            fetched_objs=obj["rules"],
                        )
                    )
        doosradb.session.commit()
        rules_tasks = filter_in_progress_tasks(rules_tasks)
        group(rules_tasks).delay()


@celery.task(name="sync_acl_rules", bind=True, base=BaseSyncTask)
def sync_acl_rules(self, identifier_args, fetched_objs, ibm_manager=None):
    """Sync all ACL Rules specific to an ACL"""
    cloud_id = identifier_args["cloud_id"]
    region = identifier_args["region"]
    acl_id = identifier_args["acl_id"]
    LOGGER.info(
        "Syncing ACLS rule for cloud '{}' and region '{}'".format(cloud_id, region)
    )
    created_or_deleted_objs = (
        doosradb.session.query(IBMNetworkAclRule)
            .filter(IBMNetworkAclRule.acl_id == acl_id, IBMNetworkAclRule.status.in_([CREATED, DELETED]))
            .all()
    )

    obj_index = set()
    for obj in fetched_objs:
        obj_index.add(obj["id"])

    for obj in created_or_deleted_objs:
        if obj.resource_id not in obj_index:
            doosradb.session.delete(obj)
            doosradb.session.commit()
    del obj_index
    del created_or_deleted_objs
    created_objs = (
        doosradb.session.query(IBMNetworkAclRule)
            .filter_by(acl_id=acl_id, status=CREATED)
            .all()
    )

    failed_objs = (
        doosradb.session.query(IBMNetworkAclRule)
            .filter(
            IBMNetworkAclRule.acl_id == acl_id,
            IBMNetworkAclRule.status.in_(
                [CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
        )
            .all()
    )

    id_index = {obj.resource_id: obj for obj in created_objs}

    name_index = {obj.name: obj for obj in failed_objs}
    del created_objs
    del failed_objs

    for obj in fetched_objs:
        try:
            existing_obj = id_index[obj["id"]]
            existing_obj.name = obj.get("name", existing_obj.name)
            existing_obj.action = obj.get("action", existing_obj.action)
            existing_obj.protocol = obj.get("protocol", existing_obj.protocol)
            existing_obj.direction = obj.get("direction", existing_obj.direction)
            existing_obj.destination = obj.get("destination", existing_obj.destination)
            existing_obj.source = obj.get("source", existing_obj.source)
            existing_obj.port_max = obj.get("port_max", existing_obj.port_max)
            existing_obj.port_min = obj.get("port_min", existing_obj.port_min)
            existing_obj.source_port_max = obj.get(
                "source_port_max", existing_obj.source_port_max
            )
            existing_obj.source_port_min = obj.get(
                "source_port_min", existing_obj.source_port_min
            )
            existing_obj.code = obj.get("code", existing_obj.code)
            existing_obj.type = obj.get("type", existing_obj.type)

        except KeyError:
            existing_obj = name_index.get(obj["name"])
            if existing_obj:
                existing_obj.resource_id = obj.get("id")
                existing_obj.status = CREATED
            else:
                ibm_network_acl_rule = IBMNetworkAclRule(
                    obj["name"],
                    obj["action"],
                    obj.get("destination"),
                    obj["direction"],
                    obj.get("source"),
                    obj["protocol"],
                    obj.get("port_max"),
                    obj.get("port_min"),
                    obj.get("source_port_max"),
                    obj.get("source_port_min"),
                    obj.get("code"),
                    obj.get("type"),
                    status=CREATED,
                    resource_id=obj["id"],
                )
                ibm_network_acl_rule.acl_id = acl_id
                doosradb.session.add(ibm_network_acl_rule)
    doosradb.session.commit()


@celery.task(name="sync_floating_ips_by_region", bind=True, base=BaseSyncTask)
def sync_floating_ips(self, identifier_args, ibm_manager=None):
    """Sync all Floating IPs in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Floating IPs cloud '{}' and region '{}'".format(group_id, region)
    )
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_floating_ips()

    for cloud in clouds:
        created_or_deleted_objs = (
            doosradb.session.query(IBMFloatingIP)
                .filter(IBMFloatingIP.cloud_id == cloud.id, IBMFloatingIP.region == region,
                        IBMFloatingIP.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMFloatingIP)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMFloatingIP)
                .filter(
                IBMFloatingIP.cloud_id == cloud.id,
                IBMFloatingIP.region == region,
                IBMFloatingIP.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )

        id_index = {obj.resource_id: obj for obj in created_objs}
        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                status = status_mapper(obj["status"])
                existing_obj.status = status
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["status"])
                    existing_obj.status = status
                else:
                    status = status_mapper(obj["status"])
                    ibm_floating_ip = IBMFloatingIP(
                        name=obj["name"],
                        region=region,
                        zone=obj["zone"],
                        address=obj["address"],
                        resource_id=obj["id"],
                        status=status,
                        cloud_id=cloud.id,
                    )
                    doosradb.session.add(ibm_floating_ip)
        doosradb.session.commit()


@celery.task(name="sync_ssh_keys_by_region", bind=True, base=BaseSyncTask)
def sync_ssh_keys(self, identifier_args, ibm_manager=None):
    """Sync all SSH Keys in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing SSH keys for group '{}' and region '{}'".format(group_id, region)
    )
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_ssh_keys()
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {group.resource_id: group.id for group in resource_groups}
        created_or_deleted_objs = (
            doosradb.session.query(IBMSshKey)
                .filter(IBMSshKey.cloud_id == cloud.id, IBMSshKey.region == region,
                        IBMSshKey.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["resource_id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMSshKey)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMSshKey)
                .filter(
                IBMSshKey.cloud_id == cloud.id,
                IBMSshKey.region == region,
                IBMSshKey.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["resource_id"]]
                resource_group = resource_groups.get(obj["resource_group_id"])
                if existing_obj.resource_group_id != resource_group:
                    existing_obj.resource_group_id = resource_group
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("resource_id")
                    existing_obj.status = CREATED
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if existing_obj.resource_group_id != resource_group:
                        existing_obj.resource_group_id = resource_group
                else:
                    new_obj = IBMSshKey(
                        name=obj["name"],
                        type_=obj["type"],
                        public_key=obj["public_key"],
                        region=region,
                        finger_print=obj["finger_print"],
                        status=CREATED,
                        resource_id=obj["resource_id"],
                        cloud_id=cloud.id,
                    )
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group
                    doosradb.session.add(new_obj)
        doosradb.session.commit()


@celery.task(name="sync_ike_policies_by_region", bind=True, base=BaseSyncTask)
def sync_ike_policies(self, identifier_args, ibm_manager=None):
    """Sync all  IKE Policies in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing IKE Policies for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_ike_policies()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {group.resource_id: group.id for group in resource_groups}
        created_or_deleted_objs = (
            doosradb.session.query(IBMIKEPolicy)
                .filter(IBMIKEPolicy.cloud_id == cloud.id, IBMIKEPolicy.region == region,
                        IBMIKEPolicy.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMIKEPolicy)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMIKEPolicy)
                .filter(
                IBMIKEPolicy.cloud_id == cloud.id,
                IBMIKEPolicy.region == region,
                IBMIKEPolicy.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )

        id_index = {obj.resource_id: obj for obj in created_objs}
        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                existing_obj.key_lifetime = obj.get(
                    "key_lifetime", existing_obj.key_lifetime
                )
                existing_obj.ike_version = obj.get("ike_version", existing_obj.ike_version)
                existing_obj.authentication_algorithm = obj.get(
                    "authentication_algorithm", existing_obj.authentication_algorithm
                )
                existing_obj.encryption_algorithm = obj.get(
                    "encryption_algorithm", existing_obj.encryption_algorithm
                )
                existing_obj.dh_group = obj.get("dh_group", existing_obj.dh_group)

                resource_group = resource_groups.get(obj["resource_group_id"])
                if existing_obj.resource_group_id != resource_group:
                    existing_obj.resource_group_id = resource_group

            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    existing_obj.status = CREATED
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        existing_obj.resource_group_id = resource_group

                else:
                    new_obj = IBMIKEPolicy(
                        name=obj["name"],
                        region=region,
                        key_lifetime=obj["key_lifetime"],
                        status=CREATED,
                        ike_version=obj["ike_version"],
                        authentication_algorithm=obj["authentication_algorithm"],
                        encryption_algorithm=obj["encryption_algorithm"],
                        dh_group=obj["dh_group"],
                        resource_id=obj["id"],
                        cloud_id=cloud.id,
                    )
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group
                    doosradb.session.add(new_obj)
        doosradb.session.commit()


@celery.task(name="sync_ipsec_policies_by_region", bind=True, base=BaseSyncTask)
def sync_ipsec_policies(self, identifier_args, ibm_manager=None):
    """Sync all  IPsec Policies in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing IPsec Policies for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_ipsec_policies()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {group.resource_id: group.id for group in resource_groups}
        created_or_deleted_objs = (
            doosradb.session.query(IBMIPSecPolicy)
                .filter(IBMIPSecPolicy.cloud_id == cloud.id, IBMIPSecPolicy.region == region,
                        IBMIPSecPolicy.status.in_([CREATED, DELETED]))
                .all()
        )
        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs

        created_objs = (
            doosradb.session.query(IBMIPSecPolicy)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMIPSecPolicy)
                .filter(
                IBMIPSecPolicy.cloud_id == cloud.id,
                IBMIPSecPolicy.region == region,
                IBMIPSecPolicy.status.in_(
                    [CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                existing_obj.key_lifetime = obj.get(
                    "key_lifetime", existing_obj.key_lifetime
                )
                existing_obj.authentication_algorithm = obj.get(
                    "authentication_algorithm", existing_obj.authentication_algorithm
                )
                existing_obj.encryption_algorithm = obj.get(
                    "encryption_algorithm", existing_obj.encryption_algorithm
                )
                existing_obj.pfs_dh_group = obj.get(
                    "pfs_dh_group", existing_obj.pfs_dh_group
                )
                resource_group = resource_groups.get(obj["resource_group_id"])
                if resource_group:
                    existing_obj.resource_group_id = resource_group

            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    existing_obj.status = CREATED
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        existing_obj.resource_group_id = resource_group
                else:
                    new_obj = IBMIPSecPolicy(
                        obj["name"],
                        region,
                        obj["key_lifetime"],
                        CREATED,
                        obj["authentication_algorithm"],
                        obj["encryption_algorithm"],
                        obj["pfs_dh_group"],
                        obj["id"],
                        cloud.id,
                    )
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group
                    doosradb.session.add(new_obj)
        doosradb.session.commit()


@celery.task(name="sync_volume_profiles_by_region", bind=True, base=BaseSyncTask)
def sync_volume_profiles_by_region(self, identifier_args, ibm_manager=None):
    """Sync all Volume Profiles in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Volume Profiles for group '{}' and region '{}'".format(
            group_id, region
        )
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_volume_profiles()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        created_objs = (
            doosradb.session.query(IBMVolumeProfile)
                .filter_by(cloud_id=cloud.id, region=region)
                .all()
        )
        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["name"])

        for obj in created_objs:
            if obj.name not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        created_objs = (
            doosradb.session.query(IBMVolumeProfile)
                .filter_by(cloud_id=cloud.id, region=region)
                .all()
        )

        id_index = {obj.name: obj for obj in created_objs}
        del created_objs

        for obj in fetched_objs:
            try:
                id_index[obj["name"]]
            except KeyError:
                ibm_volume_profile = IBMVolumeProfile(
                    name=obj["name"],
                    region=region,
                    family=obj["family"],
                    generation=obj["generation"],
                    cloud_id=cloud.id,
                )
                doosradb.session.add(ibm_volume_profile)
        doosradb.session.commit()


@celery.task(name="sync_instance_profiles", bind=True, base=BaseSyncTask)
def sync_instance_profiles(self, identifier_args, ibm_manager=None):
    """Sync all Instance Profiles in a region"""
    group_id = identifier_args["group_id"]
    LOGGER.info("Syncing Instance Profiles for group '{}'".format(group_id))
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_instance_profiles()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        created_objs = (
            doosradb.session.query(IBMInstanceProfile).filter_by(cloud_id=cloud.id).all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["name"])

        for obj in created_objs:
            if obj.name not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        created_objs = (
            doosradb.session.query(IBMInstanceProfile).filter_by(cloud_id=cloud.id).all()
        )

        id_index = {obj.name: obj for obj in created_objs}
        del created_objs

        for obj in fetched_objs:
            try:
                id_index[obj["name"]]
            except KeyError:
                ibm_instance_profile = IBMInstanceProfile(
                    name=obj["name"], family=obj["family"], cloud_id=cloud.id,
                    architecture=obj["architecture"]

                )
                doosradb.session.add(ibm_instance_profile)
        doosradb.session.commit()


@celery.task(name="sync_operating_systems", bind=True, base=BaseSyncTask)
def sync_operating_systems(self, identifier_args, ibm_manager=None):
    """Sync all Operating Systems in a region"""
    group_id = identifier_args["group_id"]
    LOGGER.info("Sync Operating Systems for group '{}'".format(group_id))
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_operating_systems()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        created_objs = (
            doosradb.session.query(IBMOperatingSystem).filter_by(cloud_id=cloud.id).all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["name"])

        for obj in created_objs:
            if obj.name not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        created_objs = (
            doosradb.session.query(IBMOperatingSystem).filter_by(cloud_id=cloud.id).all()
        )

        id_index = {obj.name: obj for obj in created_objs}
        del created_objs

        for obj in fetched_objs:
            try:
                id_index[obj["name"]]
            except KeyError:
                ibm_operating_system = IBMOperatingSystem(
                    name=obj["name"],
                    architecture=obj["architecture"],
                    family=obj["family"],
                    vendor=obj["vendor"],
                    version=obj["version"],
                    cloud_id=cloud.id,
                )
                doosradb.session.add(ibm_operating_system)
        doosradb.session.commit()


@celery.task(name="sync_dedicated_hosts", bind=True, base=BaseSyncTask)
def sync_dedicated_hosts(self, identifier_args, ibm_manager=None):
    from doosra.ibm.dedicated_hosts.utils import sync_dedicated_host_profiles
    """Sync all Dedicated Hosts in a region"""
    from doosra.common.clients.ibm_clients import DedicatedHostsClient
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info("Syncing Dedicated Host, Groups and Profiles for group '{group_id}' and region '{region}'")

    cloud_id = ibm_manager.iam_ops.cloud.id
    doosradb.session.commit()

    dh_client = DedicatedHostsClient(cloud_id=cloud_id)
    dedicated_host_group_jsons = dh_client.list_dedicated_host_groups(region=region)
    dedicated_host_jsons = dh_client.list_dedicated_hosts(region=region)

    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()

    updated_dh_group_names_list = \
        [dedicated_host_group_json["name"] for dedicated_host_group_json in dedicated_host_group_jsons]
    updated_dh_names_list = \
        [dedicated_host_json["name"] for dedicated_host_json in dedicated_host_jsons]
    for cloud in clouds:
        sync_dedicated_host_profiles(cloud_id, region)

        db_created_dedicated_host_groups = \
            cloud.dedicated_host_groups.filter_by(region=region, status=CREATED).all()

        for db_created_dedicated_host_group in db_created_dedicated_host_groups:
            if db_created_dedicated_host_group.name not in updated_dh_group_names_list:
                doosradb.session.delete(db_created_dedicated_host_group)
                doosradb.session.commit()

        db_created_dedicated_hosts = \
            cloud.dedicated_hosts.filter_by(region=region, status=CREATED).all()

        for db_created_dedicated_host in db_created_dedicated_hosts:
            if db_created_dedicated_host.name not in updated_dh_names_list:
                doosradb.session.delete(db_created_dedicated_host)
                doosradb.session.commit()

        db_dh_groups = cloud.dedicated_host_groups.filter_by(region=region).all()
        db_dh_group_name_dh_group_obj_dict = {dh_group.name: dh_group for dh_group in db_dh_groups if dh_group.name}
        for dedicated_host_group_json in dedicated_host_group_jsons:
            dh_group_resource_group = \
                cloud.resource_groups.filter_by(resource_id=dedicated_host_group_json["resource_group"]["id"]).first()
            if not dh_group_resource_group:
                LOGGER.error("what sorcery is this 1")
                continue

            supported_instance_profile_objs = []
            proceed = True
            for supported_instance_profile in dedicated_host_group_json["supported_instance_profiles"]:
                instance_profile_obj = \
                    cloud.instance_profiles.filter_by(name=supported_instance_profile["name"]).first()
                if not instance_profile_obj:
                    LOGGER.error("what sorcery is this 5")
                    proceed = False
                    break

                supported_instance_profile_objs.append(instance_profile_obj)

            if not proceed:
                continue

            if dedicated_host_group_json["name"] in db_dh_group_name_dh_group_obj_dict:
                updated_dh_group = IBMDedicatedHostGroup.from_ibm_json(dedicated_host_group_json)
                db_dh_group = db_dh_group_name_dh_group_obj_dict[dedicated_host_group_json["name"]]
                db_dh_group.update_from_obj(updated_dh_group)
                db_dh_group.cloud_id = cloud.id
                db_dh_group.resource_group_id = dh_group_resource_group.id
                db_dh_group.supported_instance_profiles = supported_instance_profile_objs
            else:
                db_dh_group = IBMDedicatedHostGroup.from_ibm_json(dedicated_host_group_json)
                db_dh_group.cloud_id = cloud.id
                db_dh_group.resource_group_id = dh_group_resource_group.id
                db_dh_group.supported_instance_profiles = supported_instance_profile_objs
                doosradb.session.add(db_dh_group)

            doosradb.session.commit()

        db_dedicated_hosts = cloud.dedicated_hosts.filter_by(region=region).all()
        db_dh_name_dh_obj_dict = {dh.name: dh for dh in db_dedicated_hosts if dh.name}
        for dedicated_host_json in dedicated_host_jsons:
            dh_resource_group = \
                cloud.resource_groups.filter_by(resource_id=dedicated_host_json["resource_group"]["id"]).first()
            if not dh_resource_group:
                LOGGER.error("what sorcery is this 2")
                continue

            dh_dh_group = \
                cloud.dedicated_host_groups.filter_by(
                    resource_id=dedicated_host_json["group"]["id"], region=region
                ).first()
            if not dh_dh_group:
                LOGGER.error("what sorcery is this 3")
                continue

            dh_dh_profile = \
                cloud.dedicated_host_profiles.filter_by(
                    name=dedicated_host_json["profile"]["name"], region=region
                ).first()
            if not dh_dh_profile:
                LOGGER.error("what sorcery is this 4")
                continue

            proceed = True
            supported_instance_profile_objs = []
            for supported_instance_profile in dedicated_host_json["supported_instance_profiles"]:
                instance_profile_obj = \
                    cloud.instance_profiles.filter_by(name=supported_instance_profile["name"]).first()
                if not instance_profile_obj:
                    LOGGER.error("what sorcery is this 6")
                    proceed = False
                    break

                supported_instance_profile_objs.append(instance_profile_obj)

            if not proceed:
                continue

            if dedicated_host_json["name"] in db_dh_name_dh_obj_dict:
                updated_dh = IBMDedicatedHost.from_ibm_json(dedicated_host_json)
                db_dh = db_dh_name_dh_obj_dict[dedicated_host_json["name"]]
                db_dh.update_from_obj(updated_dh)
                db_dh.cloud_id = cloud.id
                db_dh.resource_group_id = dh_resource_group.id
                db_dh.dedicated_host_group_id = dh_dh_group.id
                db_dh.dedicated_host_profile_id = dh_dh_profile.id
                db_dh.supported_instance_profiles = supported_instance_profile_objs

            else:
                db_dh = IBMDedicatedHost.from_ibm_json(dedicated_host_json)
                db_dh.cloud_id = cloud.id
                db_dh.resource_group_id = dh_resource_group.id
                db_dh.dedicated_host_group_id = dh_dh_group.id
                db_dh.dedicated_host_profile_id = dh_dh_profile.id
                db_dh.supported_instance_profiles = supported_instance_profile_objs
                doosradb.session.add(db_dh)

            doosradb.session.commit()

            for instance_json in dedicated_host_json["instances"]:
                db_instance = cloud.instances.filter_by(resource_id=instance_json["id"], region=region).first()
                if not db_instance:
                    continue

                db_instance.ibm_dedicated_host = db_dh
            doosradb.session.commit()


@celery.task(name="sync_volumes", bind=True, base=BaseSyncTask)
def sync_volumes(self, identifier_args, ibm_manager=None):
    """Sync all Volumes"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Volumes for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_volumes()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        volume_profiles = (
            doosradb.session.query(IBMVolumeProfile)
                .filter_by(cloud_id=cloud.id, region=region)
                .all()
        )
        volume_profiles = {profiles.name: profiles.id for profiles in volume_profiles}
        created_or_deleted_objs = (
            doosradb.session.query(IBMVolume)
                .filter(IBMVolume.cloud_id == cloud.id, IBMVolume.region == region,
                        IBMVolume.status.in_([CREATED, DELETED]))
                .all()
        )
        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMVolume)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )
        id_index = {obj.resource_id: obj for obj in created_objs}
        del created_objs
        instance_volume_task = []
        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                if not obj["volume_attachments_info"]:
                    logging.info("Volume Attachment has been removed with volume '{}' ".format(existing_obj.id))
                    if existing_obj.ibm_volume_attachment:
                        doosradb.session.delete(existing_obj.ibm_volume_attachment)
                        doosradb.session.commit()
                if obj["volume_attachments_info"]:
                    instance_volume_task.append(
                        sync_volume_attachments.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "volume_id": existing_obj.id,
                            },
                            fetched_objs=obj["volume_attachments_info"],
                        ))
            except KeyError:
                if not obj["profile_name"]:
                    continue

                volume_profile = volume_profiles.get(obj["profile_name"])
                if not volume_profile:
                    continue

                new_obj = IBMVolume(
                    name=obj["name"],
                    capacity=obj["capacity"],
                    region=region,
                    zone=obj["zone"],
                    iops=obj["iops"],
                    encryption=obj["encryption"],
                    resource_id=obj["id"],
                    cloud_id=cloud.id,
                    status=CREATED,
                )
                new_obj.volume_profile_id = volume_profile
                doosradb.session.add(new_obj)
                doosradb.session.commit()

                if not obj["volume_attachments_info"]:
                    continue

                instance_volume_task.append(
                    sync_volume_attachments.si(
                        identifier_args={
                            "cloud_id": cloud.id,
                            "region": region,
                            "volume_id": new_obj.id,
                        },
                        fetched_objs=obj["volume_attachments_info"],
                    ))
        doosradb.session.commit()
        instance_volume_task = filter_in_progress_tasks(instance_volume_task)
        group(instance_volume_task).delay()


@celery.task(name="sync_images_by_region", bind=True, base=BaseSyncTask)
def sync_images_by_region(self, identifier_args, ibm_manager=None):
    """Sync all images in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Images for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_images()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        operating_systems = (
            doosradb.session.query(IBMOperatingSystem).filter_by(cloud_id=cloud.id).all()
        )
        operating_systems = {os.name: os.id for os in operating_systems}
        created_or_deleted_objs = (
            doosradb.session.query(IBMImage)
                .filter(IBMImage.cloud_id == cloud.id, IBMImage.region == region,
                        IBMImage.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMImage)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMImage)
                .filter(
                IBMImage.cloud_id == cloud.id,
                IBMImage.region == region,
                IBMImage.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                status = status_mapper(obj["status"])
                existing_obj.status = status
                os = operating_systems.get(obj["operating_system_name"])
                if existing_obj.operating_system_id != os:
                    existing_obj.operating_system_id = os
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["status"])
                    existing_obj.status = status
                    os = operating_systems.get(obj["operating_system_name"])
                    if existing_obj.operating_system_id != os:
                        existing_obj.operating_system_id = os
                else:
                    status = status_mapper(obj["status"])
                    if status == DEPRECATED:
                        continue
                    new_obj = IBMImage(
                        name=obj["name"],
                        visibility=obj["visibility"],
                        resource_id=obj["id"],
                        cloud_id=cloud.id,
                        status=status,
                        region=region,
                        size=obj["size"],
                    )
                    os = operating_systems.get(obj["operating_system_name"])
                    if os:
                        new_obj.operating_system_id = os
                    doosradb.session.add(new_obj)
        doosradb.session.commit()


@celery.task(name="sync_security_groups", bind=True, base=BaseSyncTask)
def sync_security_groups(self, identifier_args, ibm_manager=None):
    """Sync all Security Groups in a region """
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Security Groups for group '{}' and region '{}".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_security_groups()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {
            security_group.resource_id: security_group.id
            for security_group in resource_groups
        }
        created_or_deleted_objs = (
            doosradb.session.query(IBMSecurityGroup)
                .filter(IBMSecurityGroup.cloud_id == cloud.id, IBMSecurityGroup.status.in_([CREATED, DELETED]),
                        IBMSecurityGroup.region == region)
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMSecurityGroup)
                .filter_by(cloud_id=cloud.id, status=CREATED, region=region)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMSecurityGroup)
                .filter(
                IBMSecurityGroup.cloud_id == cloud.id,
                IBMSecurityGroup.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                IBMSecurityGroup.region == region,
            )
                .all()
        )
        rules_task = []

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                resource_group = resource_groups.get(obj["resource_group_id"])
                if existing_obj.resource_group_id != resource_group:
                    existing_obj.resource_group_id = resource_group
                rules_task.append(
                    sync_security_group_rules.si(
                        identifier_args={
                            "cloud_id": cloud.id,
                            "region": region,
                            "security_group_id": existing_obj.id,
                        },
                        fetched_objs=obj.get("rules"),
                    )
                )
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    existing_obj.status = CREATED
                    resource_group = resource_groups.get(existing_obj.resource_group_id)
                    if existing_obj.resource_group_id != resource_group:
                        existing_obj.resource_group_id = resource_group
                    rules_task.append(
                        sync_security_group_rules.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "security_group_id": existing_obj.id,
                            },
                            fetched_objs=obj.get("rules"),
                        )
                    )
                else:
                    new_obj = IBMSecurityGroup(
                        name=obj["name"],
                        resource_id=obj["id"],
                        status=CREATED,
                        cloud_id=cloud.id,
                        region=region,
                    )
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group
                    existing_vpc = (
                        doosradb.session.query(IBMVpcNetwork)
                            .filter_by(cloud_id=cloud.id, resource_id=obj['vpc_id'], region=region)
                            .first()
                    )
                    if not existing_vpc:
                        continue
                    new_obj.vpc_id = existing_vpc.id
                    doosradb.session.add(new_obj)
                    rules_task.append(
                        sync_security_group_rules.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "security_group_id": new_obj.id,
                            },
                            fetched_objs=obj.get("rules"),
                        )
                    )
        doosradb.session.commit()
        rules_task = filter_in_progress_tasks(rules_task)
        group(rules_task).delay()


@celery.task(name="sync_security_group_rules", bind=True, base=BaseSyncTask)
def sync_security_group_rules(self, identifier_args, fetched_objs, ibm_manager=None):
    """Sync all Security Group Rules specfic to a Security Group"""
    cloud_id = identifier_args["cloud_id"]
    region = identifier_args["region"]
    security_group_id = identifier_args["security_group_id"]
    LOGGER.info(
        "sync Security Groups Rules for security group '{}' from cloud '{}' and region '{}'".format(
            security_group_id, cloud_id, region
        )
    )
    created_or_deleted_objs = (
        doosradb.session.query(IBMSecurityGroupRule)
            .filter(IBMSecurityGroupRule.security_group_id == security_group_id,
                    IBMSecurityGroupRule.status.in_([CREATED, DELETED]))
            .all()
    )

    obj_index = set()
    for obj in fetched_objs:
        obj_index.add(obj["id"])

    for obj in created_or_deleted_objs:
        if obj.resource_id not in obj_index:
            doosradb.session.delete(obj)
            doosradb.session.commit()
    del obj_index
    del created_or_deleted_objs
    created_objs = (
        doosradb.session.query(IBMSecurityGroupRule)
            .filter_by(security_group_id=security_group_id, status=CREATED)
            .all()
    )

    id_index = {obj.resource_id: obj for obj in created_objs}
    del created_objs

    for obj in fetched_objs:
        try:
            existing_obj = id_index[obj["id"]]
            existing_obj.direction = obj.get("direction", existing_obj.direction)
            existing_obj.protocol = obj.get("protocol", existing_obj.protocol)
            existing_obj.code = obj.get("code", existing_obj.code)
            existing_obj.type = obj.get("type", existing_obj.type)
            existing_obj.port_min = obj.get("port_min", existing_obj.port_min)
            existing_obj.port_max = obj.get("port_max", existing_obj.port_max)
            existing_obj.address = obj.get("address", existing_obj.address)
            existing_obj.cidr_block = obj.get("cidr_block", existing_obj.cidr_block)
        except KeyError:
            new_obj = IBMSecurityGroupRule(
                obj["direction"],
                obj.get("protocol"),
                obj.get("code"),
                obj.get("type"),
                obj.get("port_min"),
                obj.get("port_max"),
                obj.get("address"),
                obj.get("cidr_block"),
                resource_id=obj.get("id"),
                status=CREATED,
            )
            new_obj.security_group_id = security_group_id
            doosradb.session.add(new_obj)
    doosradb.session.commit()


@celery.task(name="sync_vpcs", bind=True, base=BaseSyncTask)
def sync_vpcs(self, identifier_args, ibm_manager=None):
    """Sync all VPC in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info("Syncing VPCS for group '{}' and region '{}'".format(group_id, region))
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_vpcs()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    vpc_tasks = []
    vpc_address_prefixes_tasks = {}
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {
            resource_group.resource_id: resource_group.id
            for resource_group in resource_groups
        }
        acls = (
            doosradb.session.query(IBMNetworkAcl)
                .filter_by(cloud_id=cloud.id, region=region)
                .all()
        )
        acls = {acl.resource_id: acl for acl in acls}

        security_groups = (
            doosradb.session.query(IBMSecurityGroup)
                .filter_by(cloud_id=cloud.id)
                .all()
        )
        security_groups = {security_group.resource_id: security_group for security_group in security_groups}

        created_or_deleted_objs = (
            doosradb.session.query(IBMVpcNetwork)
                .filter(IBMVpcNetwork.cloud_id == cloud.id, IBMVpcNetwork.region == region,
                        IBMVpcNetwork.status.in_([CREATED, DELETED]))
                .all()
        )
        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                if obj.workspace:
                    workspace = obj.workspace
                    doosradb.session.delete(workspace)
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMVpcNetwork)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMVpcNetwork)
                .filter(
                IBMVpcNetwork.cloud_id == cloud.id,
                IBMVpcNetwork.region == region,
                IBMVpcNetwork.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                status = status_mapper(obj["status"])
                existing_obj.status = status
                resource_group = resource_groups.get(obj["resource_group_id"])
                if existing_obj.resource_group_id != resource_group:
                    existing_obj.resource_group_id = resource_group

                default_network_acl = acls.get(obj["default_network_acl_id"])
                if default_network_acl:
                    default_network_acl.is_default = True
                    existing_obj.acls.append(default_network_acl)
                default_security_group = security_groups.get(obj["default_security_group_id"])
                if default_security_group:
                    default_security_group.is_default = True
                    existing_obj.security_groups.append(default_security_group)

                address_prefix_entry = vpc_address_prefixes_tasks.get(existing_obj.resource_id)
                if address_prefix_entry:
                    vpc_address_prefixes_tasks[existing_obj.resource_id].append(existing_obj.id)
                else:
                    vpc_address_prefixes_tasks[existing_obj.resource_id] = [existing_obj.id]
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["status"])
                    existing_obj.status = status
                    resource_group = resource_groups.get(obj["resource_group_id"])

                    if existing_obj.resource_group_id != resource_group:
                        existing_obj.resource_group_id = resource_group
                    default_network_acl = acls.get(obj["default_network_acl_id"])
                    if default_network_acl:
                        default_network_acl.is_default = True
                        existing_obj.acls.append(default_network_acl)
                    default_security_group = security_groups.get(obj["default_security_group_id"])
                    if default_security_group:
                        default_security_group.is_default = True
                        existing_obj.security_groups.append(default_security_group)
                else:
                    status = status_mapper(obj["status"])
                    new_obj = IBMVpcNetwork(
                        name=obj["name"],
                        region=region,
                        crn=obj['crn'],
                        classic_access=obj["classic_access"],
                        cloud_id=cloud.id,
                        resource_id=obj["id"],
                        status=status,
                    )
                    # if not new_obj.workspace:
                    #     new_obj.workspace = WorkSpace(name=obj['name'])
                    #     new_obj.workspace.project = IBMCloud.query.get(cloud_id).project

                    default_network_acl = acls.get(obj["default_network_acl_id"])
                    if default_network_acl:
                        default_network_acl.is_default = True
                        new_obj.acls.append(default_network_acl)

                    default_security_group = security_groups.get(obj["default_security_group_id"])
                    if default_security_group:
                        default_security_group.is_default = True
                        new_obj.security_groups.append(default_security_group)

                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group

                    doosradb.session.add(new_obj)
                    address_prefix_entry = vpc_address_prefixes_tasks.get(new_obj.resource_id)
                    if address_prefix_entry:
                        vpc_address_prefixes_tasks[new_obj.resource_id].append(new_obj.id)
                    else:
                        vpc_address_prefixes_tasks[new_obj.resource_id] = [new_obj.id]
        doosradb.session.commit()
    vpc_tasks.append(sync_vpc_address_prefixes.si(identifier_args={
        "group_id": group_id,
        "region": region},
        address_prefixes=vpc_address_prefixes_tasks
    ))
    vpc_tasks = filter_in_progress_tasks(vpc_tasks)
    group(vpc_tasks).delay()


@celery.task(name="sync_public_gateways", bind=True, base=BaseSyncTask)
def sync_public_gateways(self, identifier_args, ibm_manager=None):
    """Sync all public gateways in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Public Gateways for group '{}' and region '{}'".format(
            group_id, region
        )
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_public_gateways()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        created_or_deleted_objs = (
            doosradb.session.query(IBMPublicGateway)
                .filter(IBMPublicGateway.cloud_id == cloud.id, IBMPublicGateway.status.in_([CREATED, DELETED]),
                        IBMPublicGateway.region == region)
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMPublicGateway)
                .filter_by(cloud_id=cloud.id, status=CREATED, region=region)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMPublicGateway)
                .filter(
                IBMPublicGateway.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                IBMPublicGateway.cloud_id == cloud.id,
                IBMPublicGateway.region == region,
            )
                .all()
        )
        floating_ip_task = []

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                status = status_mapper(obj["status"])
                existing_obj.status = status
                existing_obj.name = obj.get("name", existing_obj.name)
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["status"])
                    existing_obj.status = status
                    existing_obj.status = status
                else:
                    status = status_mapper(obj["status"])
                    new_obj = IBMPublicGateway(
                        name=obj["name"],
                        resource_id=obj["id"],
                        status=status,
                        cloud_id=cloud.id,
                        zone=obj["zone"],
                        region=region,
                    )
                    existing_vpc = (
                        doosradb.session.query(IBMVpcNetwork)
                            .filter_by(cloud_id=cloud.id, resource_id=obj['vpc_id'], region=region)
                            .first()
                    )
                    if not existing_vpc:
                        continue
                    new_obj.vpc_id = existing_vpc.id
                    floating_ip_task.append(
                        sync_public_gateway_floating_ip.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "public_gateway_id": new_obj.id,
                            },
                            fetched_objs=obj["floating_ip"],
                        )
                    )
                    doosradb.session.add(new_obj)
        doosradb.session.commit()
        floating_ip_task = filter_in_progress_tasks(floating_ip_task)
        group(floating_ip_task).delay()


@celery.task(name="sync_public_gateway_floating_ip", bind=True, base=BaseSyncTask)
def sync_public_gateway_floating_ip(self, identifier_args, fetched_objs, ibm_manager=None):
    """Sync all public gateway floating ips"""
    cloud_id = identifier_args["cloud_id"]
    region = identifier_args["region"]
    public_gateway_id = identifier_args["public_gateway_id"]
    LOGGER.info(
        "Syncing Floating IPs for public gateway '{}' from cloud '{}' and region '{}'".format(
            public_gateway_id, cloud_id, region
        )
    )
    existing_floating_ip = (
        doosradb.session.query(IBMFloatingIP)
            .filter_by(
            resource_id=fetched_objs["id"], name=fetched_objs["name"], cloud_id=cloud_id
        )
            .first()
    )
    if not existing_floating_ip:
        return
    existing_floating_ip.public_gateway_id = public_gateway_id
    doosradb.session.commit()


@celery.task(name="sync_vpc_address_prefixes", bind=True, base=BaseSyncTask)
def sync_vpc_address_prefixes(self, identifier_args, address_prefixes, ibm_manager=None):
    """Sync all vpc address prefixes"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]

    LOGGER.info(
        "Syncing VPC for Address Prefixes for cloud '{}' and region '{}'".format(
            group_id, region
        )
    )
    for vpc_resource_id, vpc_ids in address_prefixes.items():
        fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_address_prefixes(
            vpc_id=vpc_resource_id
        )
        for vpc_id in vpc_ids:
            created_or_deleted_objs = (
                doosradb.session.query(IBMAddressPrefix)
                    .filter(IBMAddressPrefix.vpc_id == vpc_id, IBMAddressPrefix.status.in_([CREATED, DELETED]))
                    .all()
            )
            obj_index = set()
            for obj in fetched_objs:
                obj_index.add(obj["id"])

            for obj in created_or_deleted_objs:
                if obj.resource_id not in obj_index:
                    doosradb.session.delete(obj)
                    doosradb.session.commit()
            del obj_index
            del created_or_deleted_objs
            created_objs = (
                doosradb.session.query(IBMAddressPrefix)
                    .filter_by(vpc_id=vpc_id, status=CREATED)
                    .all()
            )

            failed_objs = (
                doosradb.session.query(IBMAddressPrefix)
                    .filter(
                    IBMAddressPrefix.status.in_(
                        [CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                    IBMAddressPrefix.vpc_id == vpc_id,
                )
                    .all()
            )

            id_index = {obj.resource_id: obj for obj in created_objs}

            name_index = {obj.name: obj for obj in failed_objs}
            del created_objs
            del failed_objs

            for obj in fetched_objs:
                try:
                    existing_obj = id_index[obj["id"]]
                    existing_obj.name = obj.get("name", existing_obj.name)
                except KeyError:
                    existing_obj = name_index.get(obj["name"])
                    if existing_obj:
                        existing_obj.resource_id = obj.get("id")
                        existing_obj.status = CREATED
                    else:
                        new_obj = IBMAddressPrefix(
                            name=obj["name"],
                            zone=obj["zone"],
                            address=obj["address"],
                            resource_id=obj["id"],
                            status=CREATED,
                            is_default=obj["is_default"],
                        )
                        new_obj.vpc_id = vpc_id
                        doosradb.session.add(new_obj)
            doosradb.session.commit()


@celery.task(name="sync_subnets", bind=True, base=BaseSyncTask)
def sync_subnets(self, identifier_args, ibm_manager=None):
    """Sync all subnets in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Subnets for group '{}' and region '{}".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_subnets()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        public_gateways = (
            doosradb.session.query(IBMPublicGateway)
                .filter_by(region=region, cloud_id=cloud.id)
                .all()
        )

        public_gateways = {
            public_gateway.resource_id: public_gateway.id
            for public_gateway in public_gateways
        }

        acls = doosradb.session.query(IBMNetworkAcl).filter_by(cloud_id=cloud.id).all()
        acls = {acl.resource_id: acl.id for acl in acls}

        created_or_deleted_objs = (
            doosradb.session.query(IBMSubnet)
                .filter(IBMSubnet.region == region, IBMSubnet.cloud_id == cloud.id,
                        IBMSubnet.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMSubnet)
                .filter_by(region=region, cloud_id=cloud.id, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMSubnet)
                .filter(
                IBMSubnet.cloud_id == cloud.id,
                IBMSubnet.region == region,
                IBMSubnet.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                status = status_mapper(obj["status"])
                existing_obj.status = status
                existing_obj.name = obj.get("name", existing_obj.name)

                address_prefixes = doosradb.session.query(IBMAddressPrefix).filter_by(vpc_id=existing_obj.vpc_id).all()
                for address_prefix in address_prefixes:
                    if not address_prefix.resource_id:
                        continue
                    subnet_address_prefix = validate_ip_in_range(obj['ipv4_cidr_block'], address_prefix.address)
                    if subnet_address_prefix:
                        if existing_obj.address_prefix_id != address_prefix.id:
                            existing_obj.address_prefix_id = address_prefix.id

                default_network_acl = acls.get(obj["network_acl_id"])
                if default_network_acl != existing_obj.network_acl_id:
                    existing_obj.network_acl_id = default_network_acl

                default_public_gateway = public_gateways.get(obj["public_gateway_id"])
                if default_public_gateway != existing_obj.public_gateway_id:
                    existing_obj.public_gateway_id = default_public_gateway
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["status"])
                    existing_obj.status = status

                    address_prefixes = doosradb.session.query(IBMAddressPrefix).filter_by(vpc_id=existing_obj.vpc_id).all()
                    for address_prefix in address_prefixes:
                        if not address_prefix.resource_id:
                            continue
                        subnet_address_prefix = validate_ip_in_range(obj['ipv4_cidr_block'], address_prefix.address)
                        if subnet_address_prefix:
                            if existing_obj.address_prefix_id != address_prefix.id:
                                existing_obj.address_prefix_id = address_prefix.id

                    default_network_acl = acls.get(obj["network_acl_id"])
                    if default_network_acl != existing_obj.network_acl_id:
                        existing_obj.network_acl_id = default_network_acl

                    default_public_gateway = public_gateways.get(obj["public_gateway_id"])
                    if default_public_gateway != existing_obj.public_gateway_id:
                        existing_obj.public_gateway_id = default_public_gateway
                else:
                    status = status_mapper(obj["status"])
                    new_obj = IBMSubnet(
                        name=obj["name"],
                        zone=obj["zone"],
                        ipv4_cidr_block=obj["ipv4_cidr_block"],
                        resource_id=obj["id"],
                        status=status,
                        cloud_id=cloud.id,
                        region=region,
                    )

                    existing_vpc = (
                        doosradb.session.query(IBMVpcNetwork)
                            .filter_by(cloud_id=cloud.id, resource_id=obj['vpc_id'], region=region)
                            .first()
                    )
                    if not existing_vpc:
                        continue
                    new_obj.vpc_id = existing_vpc.id
                    address_prefixes = doosradb.session.query(IBMAddressPrefix).filter_by(vpc_id=existing_vpc.id).all()
                    for address_prefix in address_prefixes:
                        if not address_prefix.resource_id:
                            continue
                        subnet_address_prefix = validate_ip_in_range(obj['ipv4_cidr_block'], address_prefix.address)
                        if subnet_address_prefix:
                            new_obj.address_prefix_id = address_prefix.id
                    default_network_acl = acls.get(obj["network_acl_id"])
                    if default_network_acl:
                        new_obj.network_acl_id = default_network_acl
                    default_public_gateway = public_gateways.get(obj["public_gateway_id"])
                    if default_public_gateway:
                        new_obj.public_gateway_id = default_public_gateway
                    doosradb.session.add(new_obj)
        doosradb.session.commit()


@celery.task(name="sync_vpn_gateways", bind=True, base=BaseSyncTask)
def sync_vpn_gateways(self, identifier_args, ibm_manager=None):
    """Sync all VPN Gateways in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing VPN Gateways for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_vpn_gateways()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {
            resource_group.resource_id: resource_group.id
            for resource_group in resource_groups
        }
        subnets = doosradb.session.query(IBMSubnet).filter_by(cloud_id=cloud.id).all()
        subnets = {subnet.resource_id: subnet.id for subnet in subnets}
        created_or_deleted_objs = (
            doosradb.session.query(IBMVpnGateway)
                .filter(IBMVpnGateway.cloud_id == cloud.id, IBMVpnGateway.region == region,
                        IBMVpnGateway.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMVpnGateway)
                .filter_by(cloud_id=cloud.id, region=region, status=CREATED)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMVpnGateway)
                .filter(
                IBMVpnGateway.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                IBMVpnGateway.region == region,
                IBMVpnGateway.cloud_id == cloud.id,
            )
                .all()
        )
        vpn_tasks = []

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                status = status_mapper(obj["status"])
                existing_obj.status = status
                resource_group = resource_groups.get(obj["resource_group_id"])
                if resource_group != existing_obj.resource_group_id:
                    existing_obj.resource_group_id = resource_group
                subnet = subnets.get(obj["subnet_id"])
                if subnet != existing_obj.subnet_id:
                    existing_obj.subnet_id = subnet
                vpn_tasks.append(
                    sync_vpn_gateway_connections.si(
                        identifier_args={
                            "cloud_id": cloud.id,
                            "region": region,
                            "vpn_resource_id": obj["id"],
                            "vpn_id": existing_obj.id,
                        }
                    )
                )
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["status"])
                    existing_obj.status = status
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group != existing_obj.resource_group_id:
                        existing_obj.resource_group_id = resource_group
                    subnet = subnets.get(obj["subnet_id"])
                    if subnet != existing_obj.subnet_id:
                        existing_obj.subnet_id = subnet
                    vpn_tasks.append(
                        sync_vpn_gateway_connections.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "vpn_resource_id": obj["id"],
                                "vpn_id": existing_obj.id,
                            }
                        )
                    )

                else:
                    status = status_mapper(obj["status"])
                    converted_date = datetime.strptime(obj["created_at"], '%Y-%m-%dT%H:%M:%S.%fZ')
                    new_obj = IBMVpnGateway(
                        name=obj["name"],
                        region=region,
                        status=status,
                        resource_id=obj["id"],
                        public_ip=obj["public_ip"],
                        created_at=converted_date,
                        gateway_status=obj["gateway_status"],
                        cloud_id=cloud.id,
                    )
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group
                    subnet = subnets.get(obj["subnet_id"])
                    if subnet:
                        new_obj.subnet_id = subnet
                        vpc_subnet = (
                            doosradb.session.query(IBMSubnet).filter_by(id=subnet).first()
                        )
                        if vpc_subnet:
                            new_obj.vpc_id = vpc_subnet.vpc_id
                            vpn_tasks.append(
                                sync_vpn_gateway_connections.si(
                                    identifier_args={
                                        "cloud_id": cloud.id,
                                        "region": region,
                                        "vpn_resource_id": obj["id"],
                                        "vpn_id": new_obj.id,
                                    }
                                )
                            )
                            doosradb.session.add(new_obj)
        doosradb.session.commit()
        vpn_tasks = filter_in_progress_tasks(vpn_tasks)
        group(vpn_tasks).delay()


@celery.task(name="sync_vpn_gateway_connections", bind=True, base=BaseSyncTask)
def sync_vpn_gateway_connections(self, identifier_args, ibm_manager=None):
    """Sync all vpn gateway connections specific to a vpn gateway"""
    cloud_id = identifier_args["cloud_id"]
    region = identifier_args["region"]
    vpn_id = identifier_args["vpn_id"]
    vpn_resource_id = identifier_args["vpn_resource_id"]
    LOGGER.info(
        "Syncing VPN Gateway Connections for cloud '{}' and region '{}'".format(
            cloud_id, region
        )
    )
    existing_ike_policies = (
        doosradb.session.query(IBMIKEPolicy).filter_by(cloud_id=cloud_id).all()
    )
    existing_ike_policies = {obj.resource_id: obj.id for obj in existing_ike_policies}
    existing_ipsec_policies = (
        doosradb.session.query(IBMIPSecPolicy).filter_by(cloud_id=cloud_id).all()
    )
    existing_ipsec_policies = {
        obj.resource_id: obj.id for obj in existing_ipsec_policies
    }
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_vpn_connections(
        vpn_resource_id
    )
    created_or_deleted_objs = (
        doosradb.session.query(IBMVpnConnection)
            .filter(IBMVpnConnection.vpn_gateway_id == vpn_id, IBMVpnConnection.status.in_([CREATED, DELETED]))
            .all()
    )

    obj_index = set()
    for obj in fetched_objs:
        obj_index.add(obj["id"])

    for obj in created_or_deleted_objs:
        if obj.resource_id not in obj_index:
            doosradb.session.delete(obj)
            doosradb.session.commit()
    del obj_index
    del created_or_deleted_objs
    created_objs = (
        doosradb.session.query(IBMVpnConnection)
            .filter_by(vpn_gateway_id=vpn_id, status=CREATED)
            .all()
    )

    failed_objs = (
        doosradb.session.query(IBMVpnConnection)
            .filter(
            IBMVpnConnection.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            IBMVpnConnection.vpn_gateway_id == vpn_id,
        )
            .all()
    )
    id_index = {obj.resource_id: obj for obj in created_objs}

    name_index = {obj.name: obj for obj in failed_objs}
    del created_objs
    del failed_objs

    for obj in fetched_objs:
        try:
            existing_obj = id_index[obj["id"]]
            existing_obj.name = obj.get("name", existing_obj.name)
            status = status_mapper(obj["vpn_status"])
            existing_obj.status = status
            existing_obj.peer_address = obj.get(
                "peer_address", existing_obj.peer_address
            )
            existing_obj.pre_shared_key = obj.get(
                "pre_shared_key", existing_obj.pre_shared_key
            )
            existing_obj.dpd_interval = obj.get(
                "dpd_interval", existing_obj.dpd_interval
            )
            existing_obj.dpd_timeout = obj.get("dpd_timeout", existing_obj.dpd_timeout)
            existing_obj.dpd_action = obj.get("dpd_action", existing_obj.dpd_action)
            existing_obj.peer_cidrs = str(obj.get("peer_cidrs", existing_obj.peer_cidrs))
            existing_obj.local_cidrs = str(obj.get("local_cidrs", existing_obj.local_cidrs))
            ike_policy = existing_ike_policies.get(obj["ike_policy_id"])
            if existing_obj.ike_policy_id != ike_policy:
                existing_obj.ike_policy_id = ike_policy
            ipsec_policy = existing_ipsec_policies.get(obj["ipsec_policy_id"])
            if existing_obj.ipsec_policy_id != ipsec_policy:
                existing_obj.ipsec_policy_id = ipsec_policy

        except KeyError:
            existing_obj = name_index.get(obj["name"])
            if existing_obj:
                existing_obj.resource_id = obj["id"]
                status = status_mapper(obj["vpn_status"])
                existing_obj.status = status
                ike_policy = existing_ike_policies.get(obj["ike_policy_id"])
                if existing_obj.ike_policy_id != ike_policy:
                    existing_obj.ike_policy_id = ike_policy
                ipsec_policy = existing_ipsec_policies.get(obj["ipsec_policy_id"])
                if existing_obj.ipsec_policy_id != ipsec_policy:
                    existing_obj.ipsec_policy_id = ipsec_policy
            else:
                status = status_mapper(obj["vpn_status"])
                converted_date = datetime.strptime(obj["created_at"], '%Y-%m-%dT%H:%M:%S.%fZ')
                new_obj = IBMVpnConnection(
                    name=obj["name"],
                    peer_address=obj["peer_address"],
                    pre_shared_key=obj["psk"],
                    local_cidrs=str(obj["local_cidrs"]),
                    peer_cidrs=str(obj["peer_cidrs"]),
                    dpd_interval=obj["dpd_interval"],
                    dpd_timeout=obj["dpd_timeout"],
                    dpd_action=obj["dpd_action"],
                    resource_id=obj["id"],
                    authentication_mode=obj["authentication_mode"],
                    created_at=converted_date,
                    status=status,
                    vpn_status=obj["vpn_status"],
                    route_mode=obj["route_mode"],
                    vpn_gateway_id=vpn_id,
                )
                ike_policy = existing_ike_policies.get(obj["ike_policy_id"])
                if ike_policy:
                    new_obj.ike_policy_id = ike_policy
                ipsec_policy = existing_ipsec_policies.get(obj["ipsec_policy_id"])
                if ipsec_policy:
                    new_obj.ipsec_policy_id = ipsec_policy
                doosradb.session.add(new_obj)
    doosradb.session.commit()


@celery.task(name="sync_transit_gateways", bind=True, base=BaseSyncTask)
def sync_transit_gateways(self, identifier_args, ibm_manager=None):
    """Sync all Transit Gateways in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Transit Gateways for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.tg_manager.push_ops.raw_fetch_ops.get_all_transit_gateways()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {
            resource_group.resource_id: resource_group.id
            for resource_group in resource_groups
        }
        created_or_deleted_objs = (
            doosradb.session.query(TransitGateway)
                .filter(TransitGateway.cloud_id == cloud.id, TransitGateway.region == region,
                        TransitGateway.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(TransitGateway)
                .filter_by(
                cloud_id=cloud.id, region=region, status=CREATED
            )
                .all()
        )

        failed_objs = (
            doosradb.session.query(TransitGateway)
                .filter(
                TransitGateway.status.in_(
                    [CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                TransitGateway.region == region,
                TransitGateway.cloud_id == cloud.id,
            )
                .all()
        )

        transit_gateway_tasks = []

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}

        del failed_objs
        del created_objs

        for obj in fetched_objs:
            try:
                if region != obj["region"]:
                    continue
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                status = status_mapper(obj["gateway_status"])
                existing_obj.status = status
                existing_obj.gateway_status = obj.get("gateway_status", existing_obj.gateway_status)
                resource_group = resource_groups.get(obj["resource_group_id"])
                if resource_group != existing_obj.resource_group_id:
                    existing_obj.resource_group_id = resource_group
                transit_gateway_tasks.append(
                    sync_transit_gateway_connections.si(
                        identifier_args={
                            "cloud_id": cloud.id,
                            "region": region,
                            "transit_gateway_resource_id": obj["id"],
                            "transit_gateway_id": existing_obj.id,
                        }
                    )
                )
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["gateway_status"])
                    existing_obj.status = status
                    existing_obj.gateway_status = obj.get("gateway_status", existing_obj.gateway_status)
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group != existing_obj.resource_group_id:
                        existing_obj.resource_group_id = resource_group
                    transit_gateway_tasks.append(
                        sync_transit_gateway_connections.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "transit_gateway_resource_id": obj["id"],
                                "transit_gatewaycloud.id_id": existing_obj.id,
                            }
                        )
                    )

                else:
                    status = status_mapper(obj["gateway_status"])
                    converted_date = datetime.strptime(obj["created_at"], '%Y-%m-%dT%H:%M:%S.%fZ')
                    new_obj = TransitGateway(
                        name=obj["name"],
                        region=region,
                        status=status,
                        resource_id=obj["id"],
                        crn=obj["crn"],
                        is_global_route=obj["is_global_route"],
                        created_at=converted_date,
                        gateway_status=obj["gateway_status"],
                        cloud_id=cloud.id,
                    )
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group
                    transit_gateway_tasks.append(
                        sync_transit_gateway_connections.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "region": region,
                                "transit_gateway_resource_id": obj["id"],
                                "transit_gateway_id": new_obj.id,
                            }
                        )
                    )
                    doosradb.session.add(new_obj)
        doosradb.session.commit()
        transit_gateway_tasks = filter_in_progress_tasks(transit_gateway_tasks)
        group(transit_gateway_tasks).delay()


@celery.task(name="sync_transit_gateway_connections", bind=True, base=BaseSyncTask)
def sync_transit_gateway_connections(self, identifier_args, ibm_manager=None):
    """Sync all transit gateway connections specific to a transit gateway"""
    cloud_id = identifier_args["cloud_id"]
    region = identifier_args["region"]
    transit_gateway_id = identifier_args["transit_gateway_id"]
    transit_gateway_resource_id = identifier_args["transit_gateway_resource_id"]
    LOGGER.info(
        "Syncing Transit Gateway Connections for cloud '{}' and region '{}'".format(
            cloud_id, region
        )
    )

    fetched_objs = ibm_manager.tg_manager.push_ops.raw_fetch_ops.get_all_transit_gateway_connections(
        transit_gateway_resource_id
    )

    created_or_deleted_objs = (
        doosradb.session.query(TransitGatewayConnection)
            .filter(TransitGatewayConnection.transit_gateway_id == transit_gateway_id,
                    TransitGatewayConnection.status.in_([CREATED, DELETED]))
            .all()
    )

    obj_index = set()
    for obj in fetched_objs:
        obj_index.add(obj["id"])

    for obj in created_or_deleted_objs:
        if obj.resource_id not in obj_index:
            doosradb.session.delete(obj)
            doosradb.session.commit()
    del obj_index
    del created_or_deleted_objs

    created_objs = (
        doosradb.session.query(TransitGatewayConnection)
            .filter_by(
            transit_gateway_id=transit_gateway_id, status=CREATED
        )
            .all()
    )

    failed_objs = (
        doosradb.session.query(TransitGatewayConnection)
            .filter(
            TransitGatewayConnection.status.in_(
                [CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            TransitGatewayConnection.transit_gateway_id == transit_gateway_id
        )
            .all()
    )
    id_index = {obj.resource_id: obj for obj in created_objs}

    name_index = {obj.name: obj for obj in failed_objs}

    del failed_objs
    del created_objs

    for obj in fetched_objs:
        try:
            existing_obj = id_index[obj["id"]]
            existing_obj.name = obj.get("name", existing_obj.name)
            status = status_mapper(obj["connection_status"])
            existing_obj.status = status
            existing_obj.connection_status = obj.get("connection_status", existing_obj.connection_status)
            existing_obj.network_id = obj.get("network_id", existing_obj.network_id)
            existing_obj.network_type = obj.get("network_type", existing_obj.network_type)
        except KeyError:
            existing_obj = name_index.get(obj["name"])
            if existing_obj:
                existing_obj.resource_id = obj["id"]
                status = status_mapper(obj["connection_status"])
                existing_obj.status = status
                existing_obj.connection_status = obj.get("connection_status", existing_obj.connection_status)
            else:
                status = status_mapper(obj["connection_status"])
                vpc = doosradb.session.query(IBMVpcNetwork).filter_by(crn=obj["network_id"]).first()
                converted_date = datetime.strptime(obj["created_at"], '%Y-%m-%dT%H:%M:%S.%fZ')

                new_obj = TransitGatewayConnection(
                    name=obj["name"],
                    network_id=obj["network_id"],
                    network_type=obj["network_type"],
                    region=region,
                    resource_id=obj["id"],
                    created_at=converted_date,
                    status=status,
                    connection_status=obj["connection_status"],
                    transit_gateway_id=transit_gateway_id
                )
                new_obj.ibm_vpc_network = vpc if obj['network_type'] == "vpc" else None
                doosradb.session.add(new_obj)
    doosradb.session.commit()


@celery.task(name="sync_load_balancers", bind=True, base=BaseSyncTask)
def sync_load_balancers(self, identifier_args, ibm_manager=None):
    """Sync all load balancers in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing load balancers for group '{}' and region '{}".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_load_balancers()
    vpc_load_balancers = {}
    for load_balancer in fetched_objs:
        vpc_load_balancer = vpc_load_balancers.get(load_balancer["subnets"][0])
        if vpc_load_balancer:
            vpc_load_balancers[load_balancer["subnets"][0]].append(load_balancer)
        else:
            vpc_load_balancers[load_balancer["subnets"][0]] = [load_balancer]
        load_balancer_tasks = []
    for subnet_id, load_balancers in vpc_load_balancers.items():
        load_balancer_tasks.append(
            sync_load_balancers_by_vpc.si(
                identifier_args={
                    "group_id": group_id,
                    "region": region,
                    "subnet_id": subnet_id,
                },
                fetched_objs=load_balancers,
            )
        )
        load_balancer_tasks = filter_in_progress_tasks(load_balancer_tasks)
        group(load_balancer_tasks).delay()


@celery.task(name="sync_load_balancers_by_vpc", bind=True, base=BaseSyncTask)
def sync_load_balancers_by_vpc(self, identifier_args, fetched_objs, ibm_manager=None):
    """Sync all Load Balancers by vpc"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    subnet_id = identifier_args["subnet_id"]
    LOGGER.info(
        "Syncing Load balancers for cloud '{}' and region '{}'".format(group_id, region)
    )
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    load_balancer_pools_task = {}
    load_balancer_listeners_task = {}
    load_balancer_task = []
    for cloud in clouds:
        existing_subnet = (
            doosradb.session.query(IBMSubnet)
                .filter_by(resource_id=subnet_id, cloud_id=cloud.id)
                .first()
        )
        if not existing_subnet:
            return
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {
            resource_group.resource_id: resource_group.id
            for resource_group in resource_groups
        }
        created_or_deleted_objs = (
            doosradb.session.query(IBMLoadBalancer)
                .filter(
                IBMLoadBalancer.cloud_id == cloud.id,
                IBMLoadBalancer.region == region,
                IBMLoadBalancer.status.in_([CREATED, DELETED]),
                IBMLoadBalancer.vpc_id == existing_subnet.vpc_id,
            )
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMLoadBalancer)
                .filter_by(
                cloud_id=cloud.id,
                region=region,
                status=CREATED,
                vpc_id=existing_subnet.vpc_id,
            )
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMLoadBalancer)
                .filter(
                IBMLoadBalancer.cloud_id == cloud.id,
                IBMLoadBalancer.region == region,
                IBMLoadBalancer.vpc_id == existing_subnet.vpc_id,
                IBMLoadBalancer.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
            )
                .all()
        )
        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs
        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                status = status_mapper(obj["provisioning_status"])
                existing_obj.status = status
                existing_obj.provisioning_status = obj.get(
                    "provisioning_status", existing_obj.provisioning_status
                )
                if obj["private_ips"]:
                    existing_obj.private_ips = {"private_ips": obj["private_ips"]}
                if obj["public_ips"]:
                    existing_obj.public_ips = {"public_ips": obj["public_ips"]}
                resource_group = resource_groups.get(obj["resource_group_id"])
                if existing_obj.resource_group_id != resource_group:
                    existing_obj.resource_group_id = resource_group
                load_balancer_task.append(
                    sync_load_balancer_subnets.si(
                        identifier_args={
                            "cloud_id": cloud.id,
                            "region": region,
                            "load_balancer_id": existing_obj.resource_id,
                        },
                        subnets=obj["subnets"],
                    )
                )
                pools_entry = load_balancer_pools_task.get(existing_obj.resource_id)
                if pools_entry:
                    load_balancer_pools_task[existing_obj.resource_id].append(existing_obj.id)
                else:
                    load_balancer_pools_task[existing_obj.resource_id] = [existing_obj.id]

                listener_entry = load_balancer_listeners_task.get(existing_obj.resource_id)
                if listener_entry:
                    load_balancer_listeners_task[existing_obj.resource_id].append(existing_obj.id)
                else:
                    load_balancer_listeners_task[existing_obj.resource_id] = [existing_obj.id]
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["provisioning_status"])
                    existing_obj.status = status
                    existing_obj.provisioning_status = obj.get(
                        "provisioning_status", existing_obj.provisioning_status
                    )
                    if obj["private_ips"]:
                        existing_obj.private_ips = {"private_ips": obj["private_ips"]}
                    if obj["public_ips"]:
                        existing_obj.public_ips = {"public_ips": obj["public_ips"]}
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if existing_obj.resource_group_id != resource_group:
                        existing_obj.resource_group_id = resource_group
                    pools_entry = load_balancer_pools_task.get(existing_obj.resource_id)
                    if pools_entry:
                        load_balancer_pools_task[existing_obj.resource_id].append(existing_obj.id)
                    else:
                        load_balancer_pools_task[existing_obj.resource_id] = [existing_obj.id]

                    listener_entry = load_balancer_listeners_task.get(existing_obj.resource_id)
                    if listener_entry:
                        load_balancer_listeners_task[existing_obj.resource_id].append(existing_obj.id)
                    else:
                        load_balancer_listeners_task[existing_obj.resource_id] = [existing_obj.id]
                else:
                    status = status_mapper(obj["provisioning_status"])
                    new_obj = IBMLoadBalancer(
                        name=obj["name"],
                        is_public=obj["is_public"],
                        region=region,
                        host_name=obj["host_name"],
                        status=status,
                        resource_id=obj["id"],
                        cloud_id=cloud.id,
                        provisioning_status=obj["provisioning_status"],
                    )
                    if obj["private_ips"]:
                        new_obj.private_ips = {"private_ips": obj["private_ips"]}
                    if obj["public_ips"]:
                        new_obj.public_ips = {"public_ips": obj["public_ips"]}
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group

                    if existing_subnet:
                        new_obj.vpc_id = existing_subnet.vpc_id
                        doosradb.session.add(new_obj)
                        load_balancer_task.append(
                            sync_load_balancer_subnets.si(
                                identifier_args={
                                    "cloud_id": cloud.id,
                                    "region": region,
                                    "load_balancer_id": new_obj.resource_id,
                                },
                                subnets=obj["subnets"],
                            )
                        )
                        pools_entry = load_balancer_pools_task.get(new_obj.resource_id)
                        if pools_entry:
                            load_balancer_pools_task[new_obj.resource_id].append(new_obj.id)
                        else:
                            load_balancer_pools_task[new_obj.resource_id] = [new_obj.id]

                        listener_entry = load_balancer_listeners_task.get(new_obj.resource_id)
                        if listener_entry:
                            load_balancer_listeners_task[new_obj.resource_id].append(new_obj.id)
                        else:
                            load_balancer_listeners_task[new_obj.resource_id] = [new_obj.id]
            doosradb.session.commit()

    load_balancer_task.append(sync_load_balancers_listeners.si(identifier_args={
        "group_id": group_id,
        "region": region
    }, load_balancers_info=load_balancer_listeners_task))
    load_balancer_task.append(sync_load_balancer_pools.si(identifier_args={
        "group_id": group_id,
        "region": region
    }, load_balancers_info=load_balancer_pools_task))
    load_balancer_task = filter_in_progress_tasks(load_balancer_task)
    group(load_balancer_task).delay()


@celery.task(name="sync_load_balancers_subnet", bind=True, base=BaseSyncTask)
def sync_load_balancer_subnets(self, identifier_args, subnets, ibm_manager=None):
    """Sync all load balancers subnets in a region"""
    cloud_id = identifier_args["cloud_id"]
    region = identifier_args["region"]
    load_balancer_id = identifier_args["load_balancer_id"]
    LOGGER.info(
        "Syncing Load balancers subnets for cloud '{}' and region '{}'".format(
            cloud_id, region
        )
    )
    load_balancer = (
        doosradb.session.query(IBMLoadBalancer)
            .filter_by(resource_id=load_balancer_id, cloud_id=cloud_id, region=region)
            .first()
    )
    if not load_balancer:
        return
    subnets_list = []
    for subnet in subnets:
        subnet = doosradb.session.query(IBMSubnet).filter_by(
            resource_id=subnet, cloud_id=cloud_id
        ).first()
        subnets_list.append(subnet)
    load_balancer.subnets = subnets_list
    doosradb.session.commit()


@celery.task(name="sync_load_balancers_pools", bind=True, base=BaseSyncTask)
def sync_load_balancer_pools(self, identifier_args, load_balancers_info, ibm_manager=None):
    """Sync all Load Balancers Pools in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Load balancers Pools for cloud '{}' and region '{}'".format(
            group_id, region
        )
    )
    pool_members_tasks = {}
    pools_task = []
    for load_balancer_resource_id, load_balancer_ids in load_balancers_info.items():
        fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_pools(
            load_balancer_id=load_balancer_resource_id
        )
        for load_balancer_id in load_balancer_ids:
            created_or_deleted_objs = (
                doosradb.session.query(IBMPool)
                    .filter(IBMPool.load_balancer_id == load_balancer_id, IBMPool.status.in_([CREATED, DELETED]))
                    .all()
            )
            obj_index = set()
            for obj in fetched_objs:
                obj_index.add(obj["id"])

            for obj in created_or_deleted_objs:
                if obj.resource_id not in obj_index:
                    doosradb.session.delete(obj)
                    doosradb.session.commit()
            del obj_index
            del created_or_deleted_objs
            created_objs = (
                doosradb.session.query(IBMPool)
                    .filter_by(load_balancer_id=load_balancer_id, status=CREATED)
                    .all()
            )

            failed_objs = (
                doosradb.session.query(IBMPool)
                    .filter(
                    IBMPool.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                    IBMPool.load_balancer_id == load_balancer_id,
                )
                    .all()
            )
            id_index = {obj.resource_id: obj for obj in created_objs}

            name_index = {obj.name: obj for obj in failed_objs}
            del created_objs
            del failed_objs
            for obj in fetched_objs:
                try:
                    existing_obj = id_index[obj["id"]]
                    existing_obj.name = obj.get("name", existing_obj.name)
                    existing_obj.algorithm = obj.get("algorithm", existing_obj.algorithm)
                    existing_obj.session_persistence = obj.get(
                        "session_persistence", existing_obj.session_persistence
                    )
                    if obj.get("health_monitor"):
                        pools_task.append(
                            sync_load_balancers_pool_health_check.si(
                                identifier_args={
                                    "group_id": group_id,
                                    "region": region,
                                    "pool_id": existing_obj.id,
                                },
                                fetched_objs=obj["health_monitor"],
                            )
                        )
                    pool_entry = pool_members_tasks.get(existing_obj.resource_id)
                    if pool_entry:
                        pool_members_tasks[existing_obj.resource_id]['pool_id'].append(existing_obj.id)
                    else:
                        pool_members_tasks[existing_obj.resource_id] = {"pool_id": [existing_obj.id],
                                                                        "load_balancer_id": load_balancer_resource_id}
                except KeyError:
                    existing_obj = name_index.get(obj["name"])
                    if existing_obj:
                        existing_obj.resource_id = obj.get("id")
                        existing_obj.status = CREATED
                        if obj.get("health_monitor"):
                            pools_task.append(
                                sync_load_balancers_pool_health_check.si(
                                    identifier_args={
                                        "group_id": group_id,
                                        "region": region,
                                        "pool_id": existing_obj.id,
                                    },
                                    fetched_objs=obj["health_monitor"],
                                )
                            )
                    else:
                        new_obj = IBMPool(
                            obj["name"],
                            obj["algorithm"],
                            obj["protocol"],
                            resource_id=obj["id"],
                            status=CREATED,
                        )

                        new_obj.load_balancer_id = load_balancer_id

                        if obj.get("session_persistence"):
                            new_obj.session_persistence = obj["session_persistence"]

                        if obj.get("health_monitor"):
                            pools_task.append(
                                sync_load_balancers_pool_health_check.si(
                                    identifier_args={
                                        "group_id": group_id,
                                        "region": region,
                                        "pool_id": new_obj.id,
                                    },
                                    fetched_objs=obj["health_monitor"],
                                )
                            )
                        pool_entry = pool_members_tasks.get(new_obj.resource_id)
                        if pool_entry:
                            pool_members_tasks[new_obj.resource_id]['pool_id'].append(new_obj.id)
                        else:
                            pool_members_tasks[new_obj.resource_id] = {"pool_id": [new_obj.id],
                                                                       "load_balancer_id": load_balancer_resource_id}
                        doosradb.session.add(new_obj)
            doosradb.session.commit()
    pools_task.append(sync_pool_members.si(identifier_args={
        "group_id": group_id,
        "region": region},
        pools_info=pool_members_tasks))
    group(filter_in_progress_tasks(pools_task)).delay()


@celery.task(name="sync_pool_members", bind=True, base=BaseSyncTask)
def sync_pool_members(self, identifier_args, pools_info, ibm_manager=None):
    """Sync all Pool Members in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Pool Members for cloud '{}' and region '{}'".format(group_id, region)
    )
    for pool_resource_id, data in pools_info.items():
        fetch_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_pool_members(
            load_balancer_id=data["load_balancer_id"], pool_id=pool_resource_id
        )
        for pool_id in data["pool_id"]:
            created_objs = doosradb.session.query(IBMPoolMember).filter_by(pool_id=pool_id, status=CREATED).all()
            creation_pending_objs = doosradb.session.query(IBMPoolMember).filter_by(pool_id=pool_id,
                                                                                    status=CREATION_PENDING).all()
            id_index = {obj.port: obj for obj in created_objs}
            name_index = {obj.port: obj for obj in creation_pending_objs}
            del created_objs
            del creation_pending_objs
            for obj in fetch_objs:
                try:
                    id_index[obj["port"]]
                    status_mapper(obj["status"])
                    doosradb.session.commit()
                except KeyError:
                    existing_obj = name_index.get(obj["port"])
                    if existing_obj:
                        existing_obj.resource_id = obj.get("id")
                        existing_obj.status = CREATED
                        doosradb.session.commit()
                    else:
                        new_obj = IBMPoolMember(obj["port"], obj["weight"], obj["id"], status=status_mapper(obj["status"]))
                        if obj.get("member_target_address"):
                            pool_lb = doosradb.session.query(IBMPool).filter_by(id=pool_id).first()
                            if not pool_lb:
                                continue
                            for subnet in pool_lb.ibm_load_balancer.subnets:
                                interface = (
                                    doosradb.session.query(IBMNetworkInterface)
                                        .filter_by(private_ip=obj["member_target_address"], subnet_id=subnet.id)
                                        .first()
                                )
                                if interface:
                                    new_obj.instance_id = interface.instance_id
                                new_obj.pool_id = pool_id
                                doosradb.session.add(new_obj)
                    doosradb.session.commit()


@celery.task(name="sync_load_balancers_pool_health_check", bind=True, base=BaseSyncTask)
def sync_load_balancers_pool_health_check(self, identifier_args, fetched_objs, ibm_manager=None):
    """Sync all Load Balancers pool health check in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    pool_id = identifier_args["pool_id"]
    LOGGER.info(
        "Syncing Load balancers Pool Health Check for cloud '{}' and region '{}'".format(
            group_id, region
        )
    )
    created_objs = (
        doosradb.session.query(IBMHealthCheck).filter_by(pool_id=pool_id).all()
    )

    obj_index = set()
    obj_index.add(fetched_objs["port"])

    for obj in created_objs:
        if obj.port not in obj_index:
            doosradb.session.delete(obj)
            doosradb.session.commit()
    del obj_index
    created_objs = (
        doosradb.session.query(IBMHealthCheck).filter_by(pool_id=pool_id).all()
    )

    id_index = {obj.port: obj for obj in created_objs}
    del created_objs

    try:
        existing_obj = id_index[fetched_objs["port"]]
        existing_obj.delay = fetched_objs.get("delay", existing_obj.delay)
        existing_obj.max_retries = fetched_objs.get(
            "max_retries", existing_obj.max_retries
        )
        existing_obj.timeout = fetched_objs.get("timeout", existing_obj.timeout)
        existing_obj.type = fetched_objs.get("type", existing_obj.type)
        existing_obj.url_path = fetched_objs.get("url_path", existing_obj.url_path)
        existing_obj.port = fetched_objs.get("port", existing_obj.port)
    except KeyError:
        new_obj = IBMHealthCheck(
            fetched_objs.get("delay"),
            fetched_objs.get("max_retries"),
            fetched_objs.get("timeout"),
            fetched_objs.get("type"),
            fetched_objs.get("url_path"),
            fetched_objs.get("port"),
        )
        new_obj.pool_id = pool_id
        doosradb.session.add(new_obj)
    doosradb.session.commit()


@celery.task(name="sync_load_balancers_listeners", bind=True, base=BaseSyncTask)
def sync_load_balancers_listeners(self, identifier_args, load_balancers_info, ibm_manager=None):
    """Sync Load Balancers Listeners in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing Load balancers listeners for cloud '{}' and region '{}'".format(
            group_id, region
        )
    )
    for load_balancer_resource_id, load_balancer_ids in load_balancers_info.items():
        fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_listeners(
            load_balancer_resource_id
        )
        for load_balancer_id in load_balancer_ids:
            created_or_deleted_objs = (
                doosradb.session.query(IBMListener)
                    .filter(IBMListener.load_balancer_id == load_balancer_id, IBMListener.status.in_([CREATED, DELETED]))
                    .all()
            )

            obj_index = set()
            for obj in fetched_objs:
                obj_index.add(obj["id"])

            for obj in created_or_deleted_objs:
                if obj.resource_id not in obj_index:
                    doosradb.session.delete(obj)
                    doosradb.session.commit()
            del obj_index
            del created_or_deleted_objs
            created_objs = (
                doosradb.session.query(IBMListener)
                    .filter_by(load_balancer_id=load_balancer_id, status=CREATED)
                    .all()
            )
            creation_pending_objs = (
                doosradb.session.query(IBMListener)
                    .filter_by(load_balancer_id=load_balancer_id, status=CREATION_PENDING)
                    .all()
            )
            id_index = {obj.resource_id: obj for obj in created_objs}
            name_index = {obj.port: obj for obj in creation_pending_objs}
            del created_objs
            del creation_pending_objs

            for obj in fetched_objs:
                try:
                    existing_obj = id_index[obj["id"]]
                    existing_obj.port = obj.get("port", existing_obj.port)
                    existing_obj.protocol = obj.get("protocol", existing_obj.protocol)
                    existing_obj.limit = obj.get("limit", existing_obj.limit)
                    existing_obj.crn = obj.get("crn", existing_obj.crn)
                    default_pool = doosradb.session.query(IBMPool).filter_by(name=obj["default_pool_name"],
                                                                             load_balancer_id=load_balancer_id).first()
                    if default_pool and existing_obj.pool_id != default_pool.id:
                        existing_obj.pool_id = default_pool.id
                except KeyError:
                    existing_obj = name_index.get(obj["port"])
                    if existing_obj:
                        existing_obj.resource_id = obj.get("id")
                        existing_obj.status = CREATED
                    else:
                        new_obj = IBMListener(
                            obj["port"],
                            obj["protocol"],
                            obj.get("limit"),
                            obj.get("crn"),
                            obj["id"],
                            CREATED,
                        )
                        default_pool = doosradb.session.query(IBMPool).filter_by(name=obj["default_pool_name"],
                                                                                 load_balancer_id=load_balancer_id).first()
                        if default_pool:
                            new_obj.pool_id = default_pool.id
                        new_obj.load_balancer_id = load_balancer_id
                        doosradb.session.add(new_obj)
                doosradb.session.commit()


@celery.task(name="sync_instances", bind=True, base=BaseSyncTask)
def sync_instances(self, identifier_args, ibm_manager=None):
    """Sync all Instances in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing instances for group '{}' and region '{}'".format(
            group_id, region
        )
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_instances()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    instance_ssh_tasks = {}
    instance_interfaces_task = {}
    for cloud in clouds:
        created_or_deleted_objs = (
            doosradb.session.query(IBMInstance)
                .filter(IBMInstance.cloud_id == cloud.id, IBMInstance.status.in_([CREATED, DELETED]),
                        IBMInstance.region == region)
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs
        created_objs = (
            doosradb.session.query(IBMInstance)
                .filter_by(cloud_id=cloud.id, status=CREATED, region=region)
                .all()
        )

        failed_objs = (
            doosradb.session.query(IBMInstance)
                .filter(
                IBMInstance.status.in_([CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                IBMInstance.cloud_id == cloud.id,
                IBMInstance.region == region,
            )
                .all()
        )

        existing_images = (
            doosradb.session.query(IBMImage).filter_by(cloud_id=cloud.id).all()
        )
        existing_images = {
            existing_image.resource_id: existing_image.id
            for existing_image in existing_images
        }
        existing_profiles = (
            doosradb.session.query(IBMInstanceProfile).filter_by(cloud_id=cloud.id).all()
        )
        existing_profiles = {
            existing_profile.name: existing_profile.id
            for existing_profile in existing_profiles
        }
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {
            resource_group.resource_id: resource_group.id
            for resource_group in resource_groups
        }

        id_index = {obj.resource_id: obj for obj in created_objs}

        name_index = {obj.name: obj for obj in failed_objs}
        del created_objs
        del failed_objs

        for obj in fetched_objs:
            try:
                existing_obj = id_index[obj["id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                status = status_mapper(obj["status"])
                existing_obj.status = status
                existing_obj.instance_status = obj.get(
                    "instance_status", existing_obj.instance_status
                )

                interface_entry = instance_interfaces_task.get(existing_obj.resource_id)
                if interface_entry:
                    if interface_entry.get('clouds'):
                        instance_interfaces_task[existing_obj.resource_id]['clouds'].append(cloud.id)
                else:
                    instance_interfaces_task[existing_obj.resource_id] = {"clouds": [cloud.id],
                                                                          "ibm_primary_network_interface_name":
                                                                              obj[
                                                                                  "ibm_primary_network_interface_name"]
                                                                          }
            except KeyError:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("id")
                    status = status_mapper(obj["status"])
                    existing_obj.status = status
                else:
                    status = status_mapper(obj["status"])
                    new_obj = IBMInstance(
                        name=obj["name"],
                        zone=obj["zone"],
                        resource_id=obj["id"],
                        status=status,
                        cloud_id=cloud.id,
                        region=region,
                        instance_status=obj["instance_status"],
                    )

                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group

                    existing_image = existing_images.get(obj["image_id"])
                    if existing_image:
                        new_obj.image_id = existing_image
                    existing_vpc = (
                        doosradb.session.query(IBMVpcNetwork)
                            .filter_by(cloud_id=cloud.id, resource_id=obj['vpc_id'], region=region)
                            .first()
                    )
                    if not existing_vpc:
                        continue
                    if existing_vpc:
                        new_obj.vpc_id = existing_vpc.id
                        profile = existing_profiles.get(obj["profile_name"])
                        if profile:
                            new_obj.instance_profile_id = profile
                            doosradb.session.add(new_obj)
                            instance_entry = instance_ssh_tasks.get(new_obj.resource_id)
                            if instance_entry:
                                instance_ssh_tasks[new_obj.resource_id].append(cloud.id)
                            else:
                                instance_ssh_tasks[new_obj.resource_id] = [cloud.id]

                            interface_entry = instance_interfaces_task.get(new_obj.resource_id)
                            if interface_entry:
                                if interface_entry.get('clouds'):
                                    instance_interfaces_task[new_obj.resource_id]['clouds'].append(cloud.id)
                            else:
                                instance_interfaces_task[new_obj.resource_id] = {"clouds": [cloud.id],
                                                                                 "ibm_primary_network_interface_name":
                                                                                     obj[
                                                                                         "ibm_primary_network_interface_name"]
                                                                                 }
        doosradb.session.commit()
    group(filter_in_progress_tasks([sync_instance_ssh_keys.si(
        identifier_args={
            "group_id": group_id,
            "region": region,
        },
        instances=instance_ssh_tasks
    ),
        sync_instance_network_interfaces.si(identifier_args={
            "group_id": group_id,
            "region": region,
        },
            instances=instance_interfaces_task)

    ])).delay()


@celery.task(name="sync_instance_ssh_keys", bind=True, base=BaseSyncTask)
def sync_instance_ssh_keys(self, identifier_args, instances, ibm_manager=None):
    """Sync all Instance SSH Keys"""

    for instance_id, clouds in instances.items():
        fetched_ssh_keys = ibm_manager.rias_ops.raw_fetch_ops.get_instance_ssh_keys(
            instance_id
        )
        for cloud_id in clouds:
            ssh_keys = doosradb.session.query(IBMSshKey).filter_by(cloud_id=cloud_id).all()
            ssh_keys = {ssh_key.resource_id: ssh_key for ssh_key in ssh_keys}

            existing_instance = (
                doosradb.session.query(IBMInstance)
                    .filter_by(cloud_id=cloud_id, resource_id=instance_id)
                    .first()
            )
            if not existing_instance:
                return
            for ssh_key in fetched_ssh_keys:
                key = ssh_keys.get(ssh_key)
                if key:
                    existing_instance.ssh_keys.append(key)
            doosradb.session.commit()


@celery.task(name="sync_instance_network_interfaces", bind=True, base=BaseSyncTask)
def sync_instance_network_interfaces(self, identifier_args, instances, ibm_manager=None):
    """Sync all Instance Network Interfaces in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    floating_ip_tasks = {}
    for instance_resource_id, data in instances.items():
        fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_instance_network_interfaces(
            instance_id=instance_resource_id)
        ibm_primary_network_interface_name = data[
            "ibm_primary_network_interface_name"
        ]
        for cloud_id in data['clouds']:
            instance = doosradb.session.query(IBMInstance).filter_by(
                cloud_id=cloud_id,
                resource_id=instance_resource_id
            ).first()
            if not instance:
                return
            created_objs = (
                doosradb.session.query(IBMNetworkInterface)
                    .filter_by(instance_id=instance.id)
                    .all()
            )
            obj_index = set()
            for obj in fetched_objs:
                obj_index.add(obj["id"])

            for obj in created_objs:
                if obj.resource_id not in obj_index:
                    doosradb.session.delete(obj)
                    doosradb.session.commit()
            del obj_index
            created_objs = (
                doosradb.session.query(IBMNetworkInterface)
                    .filter_by(instance_id=instance.id)
                    .all()
            )
            id_index = {obj.resource_id: obj for obj in created_objs}
            del created_objs

            for obj in fetched_objs:
                try:
                    existing_obj = id_index[obj["id"]]
                    if obj["subnet_id"]:
                        subnet = (
                            doosradb.session.query(IBMSubnet)
                                .filter_by(resource_id=obj["subnet_id"], cloud_id=cloud_id)
                                .first()
                        )
                        if subnet:
                            if existing_obj.subnet_id != subnet.id:
                                existing_obj.subnet_id = subnet.id

                    entry = floating_ip_tasks.get(instance_resource_id)
                    if entry:
                        floating_ip_tasks[instance_resource_id].append(existing_obj.resource_id)
                    else:
                        floating_ip_tasks[instance_resource_id] = [existing_obj.resource_id]

                    if obj["security_groups"]:
                        for sec_grp_id in obj["security_groups"]:
                            security_group = (
                                doosradb.session.query(IBMSecurityGroup)
                                    .filter_by(resource_id=sec_grp_id, cloud_id=cloud_id)
                                    .first()
                            )
                            if security_group:
                                existing_ibm_network_interfaces_security_groups = doosradb.session.query(
                                    ibm_network_interfaces_security_groups).filter_by(
                                    network_interface_id=existing_obj.id,
                                    security_group_id=security_group.id).first()
                                if not existing_ibm_network_interfaces_security_groups:
                                    existing_obj.security_groups.append(security_group)
                except KeyError:
                    new_obj = IBMNetworkInterface(
                        obj["name"],
                        resource_id=obj["id"],
                        private_ip=obj["primary_ipv4_address"],
                    )
                    new_obj.instance_id = instance.id
                    if ibm_primary_network_interface_name:
                        if ibm_primary_network_interface_name == obj["name"]:
                            new_obj.is_primary = True
                    if obj["subnet_id"]:
                        subnet = (
                            doosradb.session.query(IBMSubnet)
                                .filter_by(resource_id=obj["subnet_id"], cloud_id=cloud_id)
                                .first()
                        )
                        if subnet:
                            new_obj.subnet_id = subnet.id
                    if obj["security_groups"]:
                        for sec_grp_id in obj["security_groups"]:
                            security_group = (doosradb.session.query(IBMSecurityGroup)
                                              .filter_by(resource_id=sec_grp_id, cloud_id=cloud_id)
                                              .first()
                                              )
                            if security_group:
                                new_obj.security_groups.append(security_group)
                    doosradb.session.add(new_obj)
                    entry = floating_ip_tasks.get(instance_resource_id)
                    if entry:
                        floating_ip_tasks[instance_resource_id].append(new_obj.resource_id)
                    else:
                        floating_ip_tasks[instance_resource_id] = [new_obj.resource_id]
            doosradb.session.commit()

    group(filter_in_progress_tasks([sync_instance_floating_ips.si(identifier_args={
        "group_id": group_id,
        "region": region,
    },
        instances=floating_ip_tasks)])).delay()


@celery.task(name="sync_instance_floating_ips", bind=True, base=BaseSyncTask)
def sync_instance_floating_ips(self, identifier_args, instances, ibm_manager=None):
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()

    for instance_resource_id, instance_interfaces in instances.items():
        for interface_resource_id in set(instance_interfaces):
            floating_ip_id, floating_ip_name = ibm_manager.rias_ops.raw_fetch_ops.get_network_interface_floating_ip(
                instance_resource_id,
                interface_resource_id)
            for cloud in clouds:
                instance = doosradb.session.query(IBMInstance).filter_by(
                    cloud_id=cloud.id,
                    resource_id=instance_resource_id).first()
                if not instance:
                    return
                existing_network_interface = doosradb.session.query(IBMNetworkInterface).filter_by(
                    instance_id=instance.id,
                    resource_id=interface_resource_id
                ).first()
                if not existing_network_interface:
                    return

                if floating_ip_id and floating_ip_name:
                    floating_ip = doosradb.session.query(IBMFloatingIP).filter_by(resource_id=floating_ip_id,
                                                                                  name=floating_ip_name,
                                                                                  cloud_id=cloud.id).first()
                    if floating_ip:
                        existing_network_interface.floating_ip = floating_ip
                        doosradb.session.commit()


@celery.task(name="sync_volume_attachments", bind=True, base=BaseSyncTask)
def sync_volume_attachments(self, identifier_args, fetched_objs, ibm_manager=None):
    """Sync all Volume Attachments in a region"""
    cloud_id = identifier_args["cloud_id"]
    region = identifier_args["region"]
    volume_id = identifier_args["volume_id"]
    LOGGER.info(
        "Syncing Volume Attachments for volume '{}' from cloud '{}' and region '{}'".format(
            volume_id, cloud_id, region
        )
    )
    volume = doosradb.session.query(IBMVolume).filter_by(cloud_id=cloud_id, region=region,
                                                         id=volume_id).first()
    if not volume:
        LOGGER.info("Volume '{}' not found in database".format(volume_id))
        return

    for obj in fetched_objs:
        instance = doosradb.session.query(IBMInstance).filter_by(
            resource_id=obj["instance_id"], cloud_id=cloud_id, region=region
        ).first()
        if not instance:
            LOGGER.info("Instance with resource ID '{}' not found in database".format(obj["instance_id"]))
            continue

        existing_obj = doosradb.session.query(IBMVolumeAttachment).filter_by(
            instance_id=instance.id, type=obj["type"], resource_id=obj["id"]
        ).first()
        if existing_obj:
            existing_obj.name = obj.get("name", existing_obj.name)
        else:
            existing_obj = doosradb.session.query(IBMVolumeAttachment).filter_by(
                resource_id=None, name=obj['name'], type=obj["type"], instance_id=instance.id
            ).first()
            if existing_obj:
                existing_obj.resource_id = obj["id"]
            else:
                new_obj = IBMVolumeAttachment(obj["name"], obj["type"], is_delete=True, resource_id=obj["id"])
                new_obj.volume = volume
                new_obj.instance_id = instance.id
                doosradb.session.add(new_obj)

        if existing_obj:
            existing_obj.volume = volume
        doosradb.session.commit()


@celery.task(name="sync_k8s_clusters", bind=True, base=BaseSyncTask)
def sync_k8s_clusters(self, identifier_args, ibm_manager=None):
    """Sync all K8s Clusters in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing K8s Clusters for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_k8s_clusters()
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        resource_groups = (
            doosradb.session.query(IBMResourceGroup).filter_by(cloud_id=cloud.id).all()
        )
        resource_groups = {
            resource_group.resource_id: resource_group.id
            for resource_group in resource_groups
        }

        created_or_deleted_objs = (
            doosradb.session.query(KubernetesCluster)
                .filter(KubernetesCluster.cloud_id == cloud.id,
                        KubernetesCluster.status.in_([CREATED, DELETED]))
                .all()
        )

        obj_index = set()
        for obj in fetched_objs:
            obj_index.add(obj["resource_id"])

        for obj in created_or_deleted_objs:
            if obj.resource_id not in obj_index:
                doosradb.session.delete(obj)
                doosradb.session.commit()
        del obj_index
        del created_or_deleted_objs

        created_objs = list()
        created_objs_without_region = (
            doosradb.session.query(KubernetesCluster)
                .filter(KubernetesCluster.status.in_(
                    [CREATED]),
                KubernetesCluster.cloud_id == cloud.id,
            )
                .all()
        )

        for obj in created_objs_without_region:
            if obj.ibm_vpc_network.region == region:
                created_objs.append(obj)

        del created_objs_without_region

        failed_objs_without_region = (
            doosradb.session.query(KubernetesCluster)
                .filter(
                KubernetesCluster.status.in_(
                    [CREATING, CREATION_PENDING, ERROR_CREATING, FAILED, DELETING, ERROR_DELETING]),
                KubernetesCluster.cloud_id == cloud.id,
            )
                .all()
        )

        failed_objs = list()
        for obj in failed_objs_without_region:
            if obj.ibm_vpc_network.region == region:
                failed_objs.append(obj)

        k8s_cluster_tasks = list()
        id_index = {obj.resource_id: obj for obj in created_objs}
        name_index = {obj.name: obj for obj in failed_objs}

        del failed_objs
        del created_objs

        for obj in fetched_objs:
            try:
                if region != obj["region"]:
                    continue
                existing_obj = id_index[obj["resource_id"]]
                existing_obj.name = obj.get("name", existing_obj.name)
                status = status_mapper(obj["state"])
                existing_obj.status = status
                existing_obj.state = obj.get("state", existing_obj.state)
                existing_obj.kube_version = obj.get("kube_version", existing_obj.kube_version)
                existing_obj.pod_subnet = obj.get("pod_subnet", existing_obj.pod_subnet)
                existing_obj.service_subnet = obj.get("service_subnet", existing_obj.service_subnet)
                existing_obj.provider = obj.get("provider", existing_obj.provider)
                existing_obj.cluster_type = obj.get("type", existing_obj.cluster_type)
                resource_group = resource_groups.get(obj["resource_group_id"])
                if resource_group != existing_obj.resource_group_id:
                    existing_obj.resource_group_id = resource_group

                k8s_cluster_tasks.append(
                    sync_k8s_cluster_workerpools.si(
                        identifier_args={
                            "cloud_id": cloud.id,
                            "group_id": group_id,
                            "region": region,
                            "k8s_cluster_resource_id": obj["resource_id"]
                        }
                    )
                )

            except KeyError as e:
                existing_obj = name_index.get(obj["name"])
                if existing_obj:
                    existing_obj.resource_id = obj.get("resource_id")
                    status = status_mapper(obj["state"])
                    existing_obj.status = status
                    existing_obj.state = obj.get("state", existing_obj.state)
                    existing_obj.kube_version = obj.get("kube_version", existing_obj.kube_version)
                    existing_obj.pod_subnet = obj.get("pod_subnet", existing_obj.pod_subnet)
                    existing_obj.service_subnet = obj.get("service_subnet", existing_obj.service_subnet)
                    existing_obj.provider = obj.get("provider", existing_obj.provider)
                    existing_obj.cluster_type = obj.get("type", existing_obj.cluster_type)
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group != existing_obj.resource_group_id:
                        existing_obj.resource_group_id = resource_group

                    k8s_cluster_tasks.append(
                        sync_k8s_cluster_workerpools.si(
                            identifier_args={
                                "cloud_id": cloud.id,
                                "group_id": group_id,
                                "region": region,
                                "k8s_cluster_resource_id": obj["resource_id"]
                            }
                        )
                    )

                else:
                    existing_cluster = doosradb.session.query(KubernetesCluster).filter_by(name=obj["name"],
                                                                                                 cloud_id=cloud.id).first()

                    if region != obj["region"] or existing_cluster :
                        continue
                    status = status_mapper(obj["state"])

                    new_obj = KubernetesCluster(
                        name=obj['name'],
                        disable_public_service_endpoint=False,
                        kube_version=obj['kube_version'],
                        pod_subnet=obj['pod_subnet'],
                        provider=obj['provider'],
                        cluster_type=obj['type'],
                        service_subnet=obj['service_subnet'],
                        status=status,
                        state=obj['state'],
                        cloud_id=cloud.id,
                        resource_id=obj["resource_id"]
                    )
                    resource_group = resource_groups.get(obj["resource_group_id"])
                    if resource_group:
                        new_obj.resource_group_id = resource_group

                    worker_pools = ibm_manager.rias_ops.raw_fetch_ops.get_all_k8s_cluster_worker_pool(
                        cluster_id=obj["resource_id"])
                    existing_vpc_resource_id = worker_pools[0]['vpc_resource_id']
                    existing_vpc = (
                        doosradb.session.query(IBMVpcNetwork)
                            .filter_by(resource_id=existing_vpc_resource_id, cloud_id=cloud.id)
                            .first()
                    )
                    if not existing_vpc:
                        continue
                    new_obj.ibm_vpc_network = existing_vpc

                    existing_subnets = (
                        doosradb.session.query(IBMSubnet)
                            .filter_by(vpc_id=existing_vpc.id)
                            .all()
                    )
                    if not existing_subnets:
                        continue
                    for worker_pool in worker_pools:
                        k8s_cluster_worker_pool = KubernetesClusterWorkerPool(
                            name=worker_pool["name"],
                            disk_encryption=True,
                            flavor=worker_pool['flavor'],
                            worker_count=worker_pool['worker_count']
                        )
                        k8s_cluster_worker_pool.resource_id = worker_pool["resource_id"]
                        for worker_pool_zone in worker_pool["zones"]:
                            k8s_cluster_worker_pool_zone = KubernetesClusterWorkerPoolZone(
                                name=worker_pool_zone["name"]
                            )
                            for zone_subnet in worker_pool_zone['subnets']:
                                for subnet in existing_subnets:
                                    if subnet.resource_id == zone_subnet["subnet_id"]:
                                        k8s_cluster_worker_pool_zone.subnets.append(subnet)
                            k8s_cluster_worker_pool.zones.append(k8s_cluster_worker_pool_zone)
                        new_obj.worker_pools.append(k8s_cluster_worker_pool)
                    doosradb.session.add(new_obj)
        doosradb.session.commit()
        k8s_cluster_tasks = filter_in_progress_tasks(k8s_cluster_tasks)
        group(k8s_cluster_tasks).delay()


@celery.task(name="sync_k8s_cluster_workerpools", bind=True, base=BaseSyncTask)
def sync_k8s_cluster_workerpools(self, identifier_args, ibm_manager=None):
    """Sync all K8s Workerpools of Cluster in a region"""
    cloud_id = identifier_args["cloud_id"]
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    k8s_cluster_resource_id = identifier_args["k8s_cluster_resource_id"]

    LOGGER.info(
        "Syncing K8s Cluster WorkerPools for group '{}' and region '{}'".format(group_id, region)
    )
    fetched_objs = ibm_manager.rias_ops.raw_fetch_ops.get_all_k8s_cluster_worker_pool(cluster_id=k8s_cluster_resource_id)
    existing_cluster = (
        doosradb.session.query(KubernetesCluster)
            .filter_by(resource_id=k8s_cluster_resource_id, cloud_id=cloud_id)
            .first()
    )

    created_or_deleted_objs = (
        doosradb.session.query(KubernetesClusterWorkerPool)
            .filter(KubernetesClusterWorkerPool.kubernetes_cluster_id == existing_cluster.id)
            .all()
    )

    obj_index = set()
    for obj in fetched_objs:
        obj_index.add(obj["resource_id"])

    for obj in created_or_deleted_objs:
        if obj.resource_id not in obj_index:
            for zone_obj in obj.zones:
                doosradb.session.delete(zone_obj)
            doosradb.session.delete(obj)
            doosradb.session.commit()
    del obj_index
    del created_or_deleted_objs

    created_objs = list()
    failed_objs = list()
    if (existing_cluster.ibm_vpc_network.region == region and
            existing_cluster.cloud_id == cloud_id):
        if (existing_cluster.status == CREATED):
            created_objs = doosradb.session.query(KubernetesClusterWorkerPool).filter_by(kubernetes_cluster_id=existing_cluster.id).all()
        else:
            failed_objs = doosradb.session.query(KubernetesClusterWorkerPool).filter_by(kubernetes_cluster_id=existing_cluster.id).all()

    id_index = {obj.resource_id: obj for obj in created_objs}
    name_index = {obj.name: obj for obj in failed_objs}

    del failed_objs
    del created_objs

    for obj in fetched_objs:
        try:
            if existing_cluster.ibm_vpc_network.region != region:
                continue
            existing_obj = id_index[obj["resource_id"]]
            existing_obj.name = obj.get("name", existing_obj.name)
            existing_obj.flavor = obj.get("flavor", existing_obj.flavor)
            existing_obj.disk_encryption = True if not existing_obj.disk_encryption else existing_obj.disk_encryption
            existing_obj.worker_count = obj.get("worker_count", existing_obj.worker_count)

            ibm_workerpool_zone_names = list()
            existing_zone_names = list()
            for zone in obj["zones"]:
                ibm_workerpool_zone_names.append(zone['name'])

            for existing_zone in existing_obj.zones:
                existing_zone_names.append(existing_zone.name)
                if existing_zone.name not in ibm_workerpool_zone_names:
                    doosradb.session.delete(existing_zone)

            existing_subnets = (
                doosradb.session.query(IBMSubnet)
                    .filter_by(vpc_id=existing_cluster.ibm_vpc_network.id)
                    .all()
            )
            if not existing_subnets:
                continue

            for ibm_zone in obj["zones"]:
                if ibm_zone['name'] not in existing_zone_names:
                    new_zone = KubernetesClusterWorkerPoolZone(
                        name = ibm_zone['name']
                    )
                    new_zone.worker_pool_id = existing_obj.id
                    for zone_subnet in ibm_zone['subnets']:
                        for subnet in existing_subnets:
                            if subnet.resource_id == zone_subnet["subnet_id"]:
                                new_zone.subnets.append(subnet)
                    doosradb.session.add(new_zone)
        except KeyError as e:
            existing_obj = name_index.get(obj["name"])
            if existing_obj:
                existing_obj.resource_id = obj.get("resource_id")
                existing_obj.name = obj.get("name", existing_obj.name)
                existing_obj.disk_encryption = True if not existing_obj.disk_encryption else existing_obj.disk_encryption
                existing_obj.flavor = obj.get("flavor", existing_obj.flavor)
                existing_obj.worker_count = obj.get("worker_count", existing_obj.worker_count)

                ibm_workerpool_zone_names = list()
                existing_zone_names = list()
                for zone in obj["zones"]:
                    ibm_workerpool_zone_names.append(zone['name'])

                for existing_zone in existing_obj.zones:
                    existing_zone_names.append(existing_zone.name)
                    if existing_zone.name not in ibm_workerpool_zone_names:
                        doosradb.session.delete(existing_zone)

                existing_subnets = (
                    doosradb.session.query(IBMSubnet)
                        .filter_by(vpc_id=existing_cluster.ibm_vpc_network.id)
                        .all()
                )
                if not existing_subnets:
                    continue

                for ibm_zone in obj["zones"]:
                    if ibm_zone['name'] not in existing_zone_names:
                        new_zone = KubernetesClusterWorkerPoolZone(
                            name=ibm_zone['name']
                        )
                        new_zone.worker_pool_id = existing_obj.id
                        for zone_subnet in ibm_zone['subnets']:
                            for subnet in existing_subnets:
                                if subnet.resource_id == zone_subnet["subnet_id"]:
                                    new_zone.subnets.append(subnet)
                        doosradb.session.add(new_zone)
            else:
                if existing_cluster.ibm_vpc_network.region != region:
                    continue
                existing_vpc = doosradb.session.query(IBMVpcNetwork)\
                    .filter_by(resource_id=obj["vpc_resource_id"], cloud_id=existing_cluster.cloud_id).first()
                existing_cluster.vpc_id = existing_vpc.id
                new_obj = KubernetesClusterWorkerPool(
                    name=obj["name"],
                    disk_encryption=True,
                    flavor=obj['flavor'],
                    worker_count=obj['worker_count']
                )
                new_obj.resource_id = obj["resource_id"]
                new_obj.kubernetes_cluster_id = existing_cluster.id
                existing_subnets = (
                    doosradb.session.query(IBMSubnet)
                        .filter_by(vpc_id=existing_cluster.ibm_vpc_network.id)
                        .all()
                )
                if not existing_subnets:
                    continue

                for worker_pool_zone in obj["zones"]:
                    k8s_cluster_worker_pool_zone = KubernetesClusterWorkerPoolZone(
                        name=worker_pool_zone["name"]
                    )
                    for zone_subnet in worker_pool_zone['subnets']:
                        for subnet in existing_subnets:
                            if subnet.resource_id == zone_subnet["subnet_id"]:
                                k8s_cluster_worker_pool_zone.subnets.append(subnet)
                    new_obj.zones.append(k8s_cluster_worker_pool_zone)
                doosradb.session.add(new_obj)
        doosradb.session.commit()


@celery.task(name="sync_k8s_cluster_workloads", bind=True, base=BaseSyncTask)
def sync_k8s_cluster_workloads(self, identifier_args, ibm_manager=None):
    """Sync all K8s Clusters Workloads in a region"""
    group_id = identifier_args["group_id"]
    region = identifier_args["region"]
    LOGGER.info(
        "Syncing K8s Clusters Workloads for group '{}' and region '{}'".format(group_id, region)
    )
    clouds = doosradb.session.query(IBMCloud).filter_by(group_id=group_id, status=VALID).all()
    for cloud in clouds:
        existing_clusters = doosradb.session.query(KubernetesCluster).filter_by(cloud_id=cloud.id).all()
        if not existing_clusters:
            LOGGER.info(f"No Cluster found for Cloud ID: {cloud.id}")

        clusters = list()
        for obj in existing_clusters:
            if obj.ibm_vpc_network.region == region:
                clusters.append(obj)
        existing_clusters = clusters
        del clusters

        ibm_k8s_client = K8sClient(cloud.id)
        try:
            for cluster in existing_clusters:
                k8s_workloads_list = list()
                if cluster.ibm_vpc_network.region != region:
                    continue
                kube_config = ibm_k8s_client.get_k8s_cluster_kube_config(cluster=cluster.resource_id, resource_group=cluster.ibm_resource_group.name)
                kube_config = K8s(configuration_json=kube_config)
                namespaces = kube_config.client.CoreV1Api().list_namespace(watch=False)
                for namespace in namespaces.items:
                    temp = {"namespace": "", "pod": [], "svc": [], "pvc": []}
                    if namespace.metadata.name != "velero":
                        temp["namespace"] = namespace.metadata.name
                        pods = kube_config.client.CoreV1Api().list_namespaced_pod(namespace=namespace.metadata.name)
                        if pods.items:
                            for pod in pods.items:
                                temp["pod"].append(pod.metadata.name)
                        pvcs = kube_config.client.CoreV1Api().list_namespaced_persistent_volume_claim(
                            namespace=namespace.metadata.name)
                        if pvcs.items:
                            for pvc in pvcs.items:
                                temp["pvc"].append(
                                    {"name": pvc.metadata.name, "size": pvc.spec.resources.requests['storage']})
                        svcs = kube_config.client.CoreV1Api().list_namespaced_service(namespace=namespace.metadata.name)
                        if svcs.items:
                            for svc in svcs.items:
                                temp["svc"].append(svc.metadata.name)
                        k8s_workloads_list.append(temp)

                cluster.workloads = k8s_workloads_list
                doosradb.session.commit()
                del k8s_workloads_list
        except Exception as e:
            LOGGER.info(f"Exception occurred for Cluster Workload: {e}")


def status_mapper(status):
    if status in [AVAILABLE, ACTIVE, ATTACHED, STABLE, RUNNING, STOPPED, STOPPING, STARTING, RESUMING, RESTARTING,
                  PAUSED, PAUSING, NORMAL, WARNING, CRITICAL]:
        return CREATED
    elif status in [PENDING, CREATE_PENDING, MAINTENANCE_PENDING, UPDATE_PENDING, DEPLOYING, UPDATING, REQUESTED]:
        return CREATING
    elif status in [DELETE_PENDING, DELETING]:
        return DELETING
    elif status in [IBM_DELETING, CLUSTER_DELETED]:
        return DELETED
    else:
        return FAILED
