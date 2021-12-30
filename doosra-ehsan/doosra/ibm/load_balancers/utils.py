from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import (
    IBMLoadBalancer,
    IBMHealthCheck,
    IBMInstance,
    IBMListener,
    IBMPool,
    IBMPoolMember,
    IBMSubnet,
    IBMVpcNetwork,
)


def configure_load_balancer(data):
    """
    Configuring IBM load-balancer on IBM cloud
    :return:
    """
    ibm_load_balancer = None
    ibm_vpc_network = IBMVpcNetwork.query.get(data["vpc_id"])
    if not ibm_vpc_network:
        current_app.logger.debug(
            "IBM VPC Network with ID {} not found".format(data["vpc_id"])
        )
        return

    current_app.logger.info(
        "Deploying IBM load balancer '{name}' on IBM Cloud".format(name=data["name"])
    )
    try:
        ibm_manager = IBMManager(ibm_vpc_network.ibm_cloud, data["region"])
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(
            data["resource_group"]
        )
        if not existing_resource_group:
            raise IBMInvalidRequestError(
                "Resource Group with name '{}' not configured".format(
                    data["resource_group"]
                )
            )
        existing_resource_group = (
            existing_resource_group[0].get_existing_from_db()
            or existing_resource_group[0]
        )

        existing_load_balancer = ibm_manager.rias_ops.fetch_ops.get_all_load_balancers(
            name=data["name"]
        )
        if existing_load_balancer:
            raise IBMInvalidRequestError(
                "IBM load balancer with name '{}' already configured".format(
                    data["name"]
                )
            )

        existing_vpc = ibm_manager.rias_ops.fetch_ops.get_all_vpcs(ibm_vpc_network.name)
        if not existing_vpc:
            raise IBMInvalidRequestError(
                "IBM VPC Network with name '{}' not found".format(ibm_vpc_network.name)
            )

        ibm_load_balancer = IBMLoadBalancer(
            data["name"], data["is_public"], data["region"]
        )
        subnets_list = list()
        for subnet in data["subnets"]:
            ibm_subnet = IBMSubnet.query.get(subnet["id"])
            if not ibm_subnet:
                current_app.logger.debug(
                    "Subnet with ID {id} not found".format(id=subnet["id"])
                )
                return

            existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(
                ibm_subnet.name
            )
            if not existing_subnet:
                raise IBMInvalidRequestError(
                    "IBM Subnet with name '{}' not found".format(ibm_subnet.name)
                )
            subnets_list.append(ibm_subnet)

        pools_list = list()
        if data.get("pools"):
            for pool in data["pools"]:
                ibm_pool = IBMPool(
                    pool["name"],
                    pool["algorithm"],
                    pool["protocol"],
                    pool.get("session_persistence"),
                )
                if pool.get("health_monitor"):
                    health_check = pool["health_monitor"]
                    ibm_health_check = IBMHealthCheck(
                        delay=health_check.get("delay"),
                        max_retries=health_check.get("max_retries"),
                        timeout=health_check.get("timeout"),
                        type_=health_check.get("protocol"),
                        url_path=health_check.get("url_path"),
                        port=int(health_check.get("port")) if health_check.get("port") else None,
                    )
                    ibm_pool.health_check = ibm_health_check

                if pool.get("members"):
                    for member in pool["members"]:
                        ibm_pool_member = IBMPoolMember(
                            member.get("port"), member.get("weight")
                        )
                        instance = IBMInstance.query.get(member["instance_id"])
                        if not instance:
                            current_app.logger.debug(
                                "IBM Instance with ID {id} not found".format(
                                    id=instance["id"]
                                )
                            )
                            return

                        ibm_pool_member.instance = instance
                        ibm_pool.pool_members.append(ibm_pool_member)
                pools_list.append(ibm_pool)

        if data.get("listeners"):
            for listener in data["listeners"]:
                ibm_listener = IBMListener(
                    listener["port"],
                    listener["protocol"],
                    listener.get("connection_limit"),
                )
                if listener.get("default_pool"):
                    for pool in pools_list:
                        if pool.name == listener["default_pool"]:
                            ibm_listener.ibm_pool = pool
                            break

                ibm_load_balancer.listeners.append(ibm_listener)

        ibm_load_balancer.subnets = subnets_list
        ibm_load_balancer.pools = pools_list
        ibm_load_balancer.ibm_cloud = ibm_vpc_network.ibm_cloud
        ibm_load_balancer.ibm_vpc_network = ibm_vpc_network
        ibm_load_balancer.ibm_resource_group = existing_resource_group
        doosradb.session.add(ibm_load_balancer)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_load_balancer(ibm_load_balancer)
        existing_load_balancer = ibm_manager.rias_ops.fetch_ops.get_all_load_balancers(
            name=ibm_load_balancer.name
        )
        if existing_load_balancer:
            existing_load_balancer = existing_load_balancer[0]
            # TODO can remove this when add_update are in place
            ibm_load_balancer.resource_id = existing_load_balancer.resource_id
            ibm_load_balancer.private_ips = existing_load_balancer.private_ips
            ibm_load_balancer.public_ips = existing_load_balancer.public_ips
            ibm_load_balancer.host_name = existing_load_balancer.host_name
            ibm_load_balancer.provisioning_status = (
                existing_load_balancer.provisioning_status
            )

            for listener in ibm_load_balancer.listeners.all():
                for listener_ in existing_load_balancer.listeners.all():
                    if listener.params_eq(listener_):
                        listener.resource_id = listener_.resource_id
                        doosradb.session.commit()
                        break

            for pool in ibm_load_balancer.pools.all():
                for pool_ in existing_load_balancer.pools.all():
                    if pool.name == pool_.name:
                        pool.resource_id = pool_.resource_id
                        doosradb.session.commit()
                        break

            doosradb.session.commit()

    except (
        IBMAuthError,
        IBMConnectError,
        IBMExecuteError,
        IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_load_balancer.ibm_cloud.status = INVALID
        if ibm_load_balancer:
            ibm_load_balancer.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        for listener in ibm_load_balancer.listeners.all():
            listener.status = CREATED
            doosradb.session.commit()

        for pool in ibm_load_balancer.pools.all():
            pool.status = CREATED
            doosradb.session.commit()

        ibm_load_balancer.status = CREATED
        doosradb.session.commit()

    return ibm_load_balancer


def delete_load_balancer(ibm_load_balancer):
    """
    This request deletes a Load Balancer from IBM cloud
    :return:
    """
    current_app.logger.info(
        "Deleting IBM load balancer '{name}' on IBM Cloud".format(
            name=ibm_load_balancer.name
        )
    )
    try:
        ibm_manager = IBMManager(
            ibm_load_balancer.ibm_cloud, ibm_load_balancer.ibm_vpc_network.region
        )
        existing_load_balancer = ibm_manager.rias_ops.fetch_ops.get_all_load_balancers(
            name=ibm_load_balancer.name
        )
        if existing_load_balancer:
            ibm_manager.rias_ops.delete_load_balancer(existing_load_balancer[0])
        ibm_load_balancer.status = DELETED
        doosradb.session.commit()

    except (
        IBMAuthError,
        IBMConnectError,
        IBMExecuteError,
        IBMInvalidRequestError,
    ) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_load_balancer.ibm_cloud.status = INVALID
        if ibm_load_balancer:
            ibm_load_balancer.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_load_balancer.status = DELETED
        doosradb.session.delete(ibm_load_balancer)
        doosradb.session.commit()
        return True
