import logging

from celery import chord, group, chain

from doosra import db as doosradb
from doosra.common.consts import CREATED, CREATING, IN_PROGRESS, FAILED, SUCCESS
from doosra.common.utils import DELETING, DELETED
from doosra.ibm.common.billing_utils import log_resource_billing, IBMResourceGroup
from doosra.ibm.common.consts import PROVISIONING, VALIDATION
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.ibm.managers.exceptions import (
    IBMInvalidRequestError,
)
from doosra.models import (
    IBMIKEPolicy,
    IBMIPSecPolicy,
    IBMVpnGateway,
    IBMVpnConnection
)
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_group_tasks, update_ibm_task

LOGGER = logging.getLogger("vpn_tasks.py")


@celery.task(name="validate_ibm_ike_policy", base=IBMBaseTask, bind=True)
def task_validate_ibm_ike_policy(self, task_id, cloud_id, region, ike_policy):
    """Check if IKE policy already exists"""

    self.resource_name = ike_policy["name"]
    self.resource_type = 'ike_policies'
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    existing_ike_policy = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_ike_policies(name=ike_policy["name"])
    if existing_ike_policy:
        raise IBMInvalidRequestError(
            "IBM IKE Policy with name '{}' already configured".format(
                ike_policy["name"]
            )
        )
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info(
        "IBM IKE Policy with name '{}' validated successfully".format(ike_policy["name"])
    )


@celery.task(name="validate_ibm_ipsec_policy", base=IBMBaseTask, bind=True)
def task_validate_ibm_ipsec_policy(self, task_id, cloud_id, region, ipsec_policy):
    """Check if IPSEC policy already exists"""
    self.resource_name = ipsec_policy["name"]
    self.resource_type = 'ipsec_policies'
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )

    existing_ipsec_policy = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_ipsec_policies(name=ipsec_policy)
    if existing_ipsec_policy:
        raise IBMInvalidRequestError(
            "IBM IPSec Policy with name '{}' already configured".format(ipsec_policy["name"]))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info(
        "IBM IPSec Policy with name '{}' validated successfully".format(
            ipsec_policy["name"]))


@celery.task(name="create_ibm_ike_policy", base=IBMBaseTask, bind=True)
def task_create_ibm_ike_policy(self, task_id, cloud_id, region, ike_policy_id):
    """Create and configure ike policy"""

    ibm_ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(id=ike_policy_id).first()
    if not ibm_ike_policy:
        return

    self.resource_type = "ike_policies"
    self.resource = ibm_ike_policy
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_ike_policy = self.ibm_manager.rias_ops.fetch_ops.get_all_ike_policies(name=ibm_ike_policy.name)
    configured_ike_policy = configured_ike_policy[0] if configured_ike_policy else None
    if not configured_ike_policy:
        ibm_ike_policy.status = CREATING
        doosradb.session.commit()
        configured_ike_policy = configure_and_save_obj_confs(self.ibm_manager, ibm_ike_policy)

    ibm_ike_policy.status = CREATED
    ibm_ike_policy.resource_id = configured_ike_policy.resource_id
    doosradb.session.commit()

    LOGGER.info(
        "IBM IKE Policy with name '{}' created successfully".format(ibm_ike_policy.name)
    )

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_ike_policy)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="create_ibm_ipsec_policy", base=IBMBaseTask, bind=True)
def task_create_ibm_ipsec_policy(self, task_id, cloud_id, region, ipsec_policy_id):
    """Create and configure IPSec policy"""

    ibm_ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(id=ipsec_policy_id).first()
    if not ibm_ipsec_policy:
        return

    self.resource_type = "ipsec_policies"
    self.resource = ibm_ipsec_policy
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_ipsec_policy = self.ibm_manager.rias_ops.fetch_ops.get_all_ipsec_policies(name=ibm_ipsec_policy.name)
    configured_ipsec_policy = configured_ipsec_policy[0] if configured_ipsec_policy else None
    if not configured_ipsec_policy:
        ibm_ipsec_policy.status = CREATING
        doosradb.session.commit()
        configured_ipsec_policy = configure_and_save_obj_confs(self.ibm_manager, ibm_ipsec_policy)

    ibm_ipsec_policy.status = CREATED
    ibm_ipsec_policy.resource_id = configured_ipsec_policy.resource_id
    doosradb.session.commit()

    LOGGER.info(
        "IBM IPSec policy with name '{}' created successfully".format(
            ibm_ipsec_policy.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_ipsec_policy)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="create_ibm_vpn", base=IBMBaseTask, bind=True)
def task_create_ibm_vpn(self, task_id, cloud_id, region, vpn_id):
    """Create and configure VPN and Connections """

    ibm_vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(id=vpn_id).first()
    if not ibm_vpn_gateway:
        return

    ibm_vpn_gateway.status = CREATING
    doosradb.session.commit()
    self.resource = ibm_vpn_gateway
    self.resource_type = "vpn_gateways"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_vpn_gateway = configure_and_save_obj_confs(self.ibm_manager, ibm_vpn_gateway)
    ibm_vpn_gateway.status = CREATED
    ibm_vpn_gateway.resource_id = configured_vpn_gateway.resource_id
    ibm_vpn_gateway.gateway_status = configured_vpn_gateway.gateway_status
    ibm_vpn_gateway.public_ip = configured_vpn_gateway.public_ip
    doosradb.session.commit()
    LOGGER.info("IBM VPN with name '{}' created successfully".format(ibm_vpn_gateway.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_vpn_gateway)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="create_ibm_vpn_connection", base=IBMBaseTask, bind=True)
def task_configure_ibm_vpn_connection(self, task_id, cloud_id, region, vpn_connection_id, resource_group=None):
    """Configure vpn connection"""

    ibm_vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=vpn_connection_id).first()
    if not ibm_vpn_connection:
        return

    if resource_group:
        ibm_resource_group = IBMResourceGroup(name=resource_group, cloud_id=cloud_id)
        ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
        ibm_vpn_connection.ibm_resource_group = ibm_resource_group
    doosradb.session.commit()

    self.resource = ibm_vpn_connection
    self.resource_type = "vpn_connections"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS
    )
    configured_vpn_connection = configure_and_save_obj_confs(self.ibm_manager, ibm_vpn_connection)
    ibm_vpn_connection = configured_vpn_connection.make_copy().add_update_db(ibm_vpn_connection.ibm_vpn_gateway)
    LOGGER.info("IBM VPN Connection with name '{}' created successfully".format(ibm_vpn_connection.name))

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_vpn_connection)

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="task_delete_ibm_vpn_gateway", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpn_gateway(self, task_id, cloud_id, region, vpn_id):
    """
    This request deletes a VPN Gateway and its connections
    @return:
    """
    ibm_vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(id=vpn_id).first()
    if not ibm_vpn_gateway:
        return

    self.resource = ibm_vpn_gateway
    ibm_vpn_gateway.status = DELETING
    doosradb.session.commit()

    fetched_vpn_gateway = self.ibm_manager.rias_ops.fetch_ops.get_all_vpn_gateways(
        name=ibm_vpn_gateway.name, vpc_name=ibm_vpn_gateway.ibm_vpc_network.name,
        required_relations=False
    )

    if fetched_vpn_gateway:
        self.ibm_manager.rias_ops.delete_vpn_gateway(fetched_vpn_gateway[0])

    ibm_vpn_gateway.status = DELETED
    doosradb.session.delete(ibm_vpn_gateway)
    doosradb.session.commit()
    LOGGER.info("VPN Gateway '{name}' deleted successfully on IBM Cloud".format(name=ibm_vpn_gateway.name))


@celery.task(name="task_delete_ibm_vpn_gateway_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpn_gateway_workflow(self, task_id, cloud_id, region, vpn_id):
    """
    This request is workflow for vpn deletion
    @return:
    """
    workflow_steps = list()

    ibm_vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(id=vpn_id).first()
    if not ibm_vpn_gateway:
        return

    workflow_steps.append(task_delete_ibm_vpn_gateway.si(task_id=task_id, cloud_id=cloud_id,
                                                         region=region, vpn_id=vpn_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_delete_ibm_vpn_connection", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpn_connection(self, task_id, cloud_id, region, vpn_connection_id):
    """
    This request deletes a Vpn Connection of Vpn Gateway
    @return:
    """
    ibm_vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=vpn_connection_id).first()

    if not ibm_vpn_connection:
        return

    self.resource = ibm_vpn_connection
    ibm_vpn_connection.status = DELETING
    doosradb.session.commit()

    fetched_vpn_connection = self.ibm_manager.rias_ops.fetch_ops.get_all_vpn_connections(
        name=ibm_vpn_connection.name,
        vpn_gateway_id=ibm_vpn_connection.ibm_vpn_gateway.resource_id
    )
    if fetched_vpn_connection:
        self.ibm_manager.rias_ops.delete_vpn_connection(
            vpn_connection_obj=fetched_vpn_connection[0],
            vpn_gateway_id=ibm_vpn_connection.ibm_vpn_gateway.resource_id,
        )

    ibm_vpn_connection.status = DELETED
    doosradb.session.delete(ibm_vpn_connection)
    doosradb.session.commit()
    LOGGER.info("Vpn Connection '{name}' deleted successfully on IBM Cloud".format(name=ibm_vpn_connection.name))


@celery.task(name="task_delete_ibm_vpn_connection_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_vpn_connection_workflow(self, task_id, cloud_id, region, vpn_connection_id):
    """
    This request is workflow for the deletion of Vpn Connection of Vpn Gateway
    @return:
    """
    workflow_steps = list()

    ibm_vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=vpn_connection_id).first()
    if not ibm_vpn_connection:
        return

    workflow_steps.append(task_delete_ibm_vpn_connection.si(task_id=task_id, cloud_id=cloud_id,
                                                            region=region,
                                                            vpn_connection_id=vpn_connection_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_delete_ibm_ike_policy", base=IBMBaseTask, bind=True)
def task_delete_ibm_ike_policy(self, task_id, cloud_id, region, ike_policy_id):
    """
    This request Ike Policy of A VPN
    @return:
    """
    ibm_ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(id=ike_policy_id).first()
    if not ibm_ike_policy:
        return

    self.resource = ibm_ike_policy
    ibm_ike_policy.status = DELETING
    doosradb.session.commit()

    fetched_ike_policy = self.ibm_manager.rias_ops.fetch_ops.get_all_ike_policies(
        name=ibm_ike_policy.name,
        required_relations=False
    )

    if fetched_ike_policy:
        self.ibm_manager.rias_ops.delete_ike_policy(fetched_ike_policy[0])

    ibm_ike_policy.status = DELETED
    doosradb.session.delete(ibm_ike_policy)
    doosradb.session.commit()
    LOGGER.info("IKE Policy '{name}' deleted successfully on IBM Cloud".format(name=ibm_ike_policy.name))


@celery.task(name="task_delete_ibm_ipsec_policy", base=IBMBaseTask, bind=True)
def task_delete_ibm_ipsec_policy(self, task_id, cloud_id, region, ipsec_policy_id):
    """
    This request deletes Ipsec Policy of a VPN Gateway
    @return:
    """

    ibm_ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(id=ipsec_policy_id).first()
    if not ibm_ipsec_policy:
        return

    self.resource = ibm_ipsec_policy
    ibm_ipsec_policy.status = DELETING
    doosradb.session.commit()

    fetched_ipsec_policy = self.ibm_manager.rias_ops.fetch_ops.get_all_ipsec_policies(
        name=ibm_ipsec_policy.name,
        required_relations=False
    )

    if fetched_ipsec_policy:
        self.ibm_manager.rias_ops.delete_ipsec_policy(fetched_ipsec_policy[0])

    ibm_ipsec_policy.status = DELETED
    doosradb.session.delete(ibm_ipsec_policy)
    doosradb.session.commit()
    LOGGER.info("IP-SEC Policy '{name}' deleted successfully on IBM Cloud".format(name=ibm_ipsec_policy.name))


@celery.task(name="task_delete_ibm_ipsec_policy_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_ipsec_policy_workflow(self, task_id, cloud_id, region, ipsec_policy_id):
    """
    This request deletes ipsec policy and vpn connection
    @return:
    """

    workflow_steps, vpn_connections_tasks_list = list(), list()
    ibm_ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(id=ipsec_policy_id).first()
    if not ibm_ipsec_policy:
        return

    for vpn_connection in ibm_ipsec_policy.vpn_connections.all():
        vpn_connections_tasks_list.append(task_delete_ibm_vpn_connection.si(task_id=task_id,
                                                                            cloud_id=cloud_id, region=region,
                                                                            vpn_connection_id=vpn_connection.id))

    if vpn_connections_tasks_list and len(vpn_connections_tasks_list) == 1:
        workflow_steps.extend(vpn_connections_tasks_list)
    elif vpn_connections_tasks_list:
        workflow_steps.append(
            chord(group(vpn_connections_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="VPN Connection's Tasks Chord Finisher")))

    workflow_steps.append(task_delete_ibm_ipsec_policy.si(task_id=task_id,
                                                          cloud_id=cloud_id, region=region,
                                                          ipsec_policy_id=ibm_ipsec_policy.id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_delete_ibm_ike_policy_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_ike_policy_workflow(self, task_id, cloud_id, region, ike_policy_id):
    """
    This request deletes ike policy and vpn connection
    @return:
    """
    workflow_steps, vpn_connections_tasks_list = list(), list()
    ibm_ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(id=ike_policy_id).first()
    if not ibm_ike_policy:
        return

    for vpn_connection in ibm_ike_policy.vpn_connections.all():
        vpn_connections_tasks_list.append(task_delete_ibm_vpn_connection.si(task_id=task_id,
                                                                            cloud_id=cloud_id, region=region,
                                                                            vpn_connection_id=vpn_connection.id))

    if vpn_connections_tasks_list and len(vpn_connections_tasks_list) == 1:
        workflow_steps.extend(vpn_connections_tasks_list)
    elif vpn_connections_tasks_list:
        workflow_steps.append(
            chord(group(vpn_connections_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="VPN Connection's Tasks Chord Finisher")))

    workflow_steps.append(task_delete_ibm_ike_policy.si(task_id=task_id,
                                                        cloud_id=cloud_id, region=region,
                                                        ike_policy_id=ibm_ike_policy.id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="update_local_cidr_connection", base=IBMBaseTask, bind=True)
def task_update_local_cidr_connection(self, task_id, cloud_id, region, prefix, prefix_length, gateway_resource_id,
                                      connection_id):
    """
    This request deletes ike policy and vpn connection
    @return:
    """
    vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=connection_id).first()
    self.resource = vpn_connection
    self.resource_type = "adding_local_cidrs"
    self.vpn_cidr = "{prefix}/{prefix_length}".format(prefix=prefix, prefix_length=prefix_length)
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=IN_PROGRESS)
    self.ibm_manager.rias_ops.add_local_cidrs_connection(gateway_resource_id, vpn_connection, prefix,
                                                         prefix_length)
    LOGGER.info("Local CIDR '{prefix}' set successfully on IBM Cloud".format(prefix=prefix))
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=SUCCESS)


@celery.task(name="update_peer_cidr_connection", base=IBMBaseTask, bind=True)
def task_update_peer_cidr_connection(self, task_id, cloud_id, region, prefix, prefix_length, gateway_resource_id,
                                     connection_id):
    """
    This request deletes ike policy and vpn connection
    @return:
    """
    vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=connection_id).first()
    self.resource = vpn_connection
    self.resource_type = "adding_peer_cidrs"
    self.vpn_cidr = "{prefix}/{prefix_length}".format(prefix=prefix, prefix_length=prefix_length)
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=IN_PROGRESS)
    self.ibm_manager.rias_ops.add_peer_cidrs_connection(gateway_resource_id, vpn_connection, prefix,
                                                        prefix_length)
    LOGGER.info("Peer CIDR '{prefix}' set successfully on IBM Cloud".format(prefix=prefix))
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=SUCCESS)


@celery.task(name="delete_local_cidr_connection", base=IBMBaseTask, bind=True)
def task_delete_local_cidr_connection(self, task_id, cloud_id, region, prefix, prefix_length, gateway_resource_id,
                                      connection_id):
    """
    This request deletes ike policy and vpn connection
    @return:
    """
    vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=connection_id).first()
    self.resource = vpn_connection
    self.resource_type = "deleting_local_cidrs"
    self.vpn_cidr = "{prefix}/{prefix_length}".format(prefix=prefix, prefix_length=prefix_length)
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=IN_PROGRESS)
    existing = self.ibm_manager.rias_ops.fetch_ops.get_local_cidr(gateway_resource_id, vpn_connection.resource_id,
                                                                  prefix, prefix_length)

    if existing:
        self.ibm_manager.rias_ops.delete_local_cidrs_connection(gateway_resource_id, vpn_connection, prefix,
                                                                prefix_length)
    LOGGER.info("Local CIDR '{prefix}' delete successfully on IBM Cloud".format(prefix=prefix))
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=SUCCESS)


@celery.task(name="delete_peer_cidr_connection", base=IBMBaseTask, bind=True)
def task_delete_peer_cidr_connection(self, task_id, cloud_id, region, prefix, prefix_length, gateway_resource_id,
                                     connection_id):
    """
    This request deletes ike policy and vpn connection
    @return:
    """
    vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=connection_id).first()
    self.resource = vpn_connection
    self.resource_type = "deleting_peer_cidrs"
    self.vpn_cidr = "{prefix}/{prefix_length}".format(prefix=prefix, prefix_length=prefix_length)
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=IN_PROGRESS)
    existing = self.ibm_manager.rias_ops.fetch_ops.get_peer_cidr(gateway_resource_id, vpn_connection.resource_id,
                                                                 prefix, prefix_length)

    if existing:
        self.ibm_manager.rias_ops.delete_peer_cidrs_connection(gateway_resource_id, vpn_connection, prefix,
                                                               prefix_length)
    LOGGER.info("Peer CIDR '{prefix}' delete successfully on IBM Cloud".format(prefix=prefix))
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.vpn_cidr, resource_type=self.resource_type,
                                       stage=PROVISIONING, status=SUCCESS)


def list_diff(list1, list2):
    return list(set(list1) - set(list2))
