from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import *
from doosra.gcp.clouds.consts import INVALID
from doosra.gcp.load_balancers.consts import *
from doosra.gcp.managers.exceptions import *
from doosra.gcp.managers.gcp_manager import GCPManager
from doosra.models.gcp_models import GcpBackend, GcpBackendService, GcpForwardingRule, GcpHealthCheck, \
    GcpHostRule, GcpPortHealthCheck, GcpInstanceGroup, GcpLoadBalancer, GcpPathMatcher, GcpPathRule, GcpTargetProxy, \
    GcpUrlMap


def deploy_load_balancer(cloud_project, load_balancer_name, data):
    """
    Deploy Load balancer on Google Cloud Platform
    :return:
    """
    objs_to_configure, gcp_load_balancer = list(), None
    current_app.logger.info("Deploying Load-Balancer '{name}' on GCP cloud project '{project}'".format(
        name=load_balancer_name, project=cloud_project.name))
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        url_maps = gcp_manager.compute_engine_operations.fetch_ops.get_url_maps(
            cloud_project.project_id, name=load_balancer_name)
        if url_maps:
            raise CloudInvalidRequestError(
                "Load-Balancer with name '{}' already configured on GCP cloud".format(load_balancer_name))

        gcp_load_balancer = GcpLoadBalancer(load_balancer_name)
        gcp_load_balancer.gcp_cloud_project = cloud_project
        gcp_url_map = GcpUrlMap(load_balancer_name, type_="LOAD-BALANCER", description="CREATED BY VPC+")
        backend_services_list = list()
        for backend_service in data.get('backend_services'):
            existing_backend_service = gcp_manager.compute_engine_operations.fetch_ops.get_backend_services(
                cloud_project.project_id, name=backend_service['name'])
            if existing_backend_service:
                raise CloudInvalidRequestError(
                    "Backend service with name '{}' already exists".format(backend_service['name']))
            gcp_backend_service = GcpBackendService(
                backend_service.get('name'), backend_service.get('protocol'), backend_service.get('protocol'),
                backend_service.get('port'), backend_service.get('timeout') or "30",
                backend_service.get('description'))
            gcp_backend_service.gcp_cloud_project = cloud_project
            for backend in backend_service.get('backends'):
                gcp_backend = GcpBackend(backend.get('max_cpu_utilization'), backend.get('capacity_scaler'),
                                         backend.get('description'))
                instance_group = doosradb.session.query(GcpInstanceGroup).filter_by(
                    id=backend['instance_group_id']).first()
                existing_instance_group = gcp_manager.compute_engine_operations.fetch_ops.get_instance_groups(
                    cloud_project.project_id, zone=instance_group.zone, name=instance_group.name)
                if not existing_instance_group:
                    raise CloudInvalidRequestError(
                        "GcpInstanceGroup with name '{}' not found".format(instance_group.name))
                gcp_backend.instance_group = instance_group
                gcp_backend_service.backends.append(gcp_backend)
            if backend_service.get("health_check"):
                health_check = backend_service.get("health_check")
                gcp_health_check = GcpHealthCheck(health_check.get("name"),
                                                  health_check.get("protocol") or "TCP",
                                                  health_check.get("description"),
                                                  health_check.get("healthy_threshold"),
                                                  health_check.get("unhealthy_threshold"),
                                                  health_check.get("timeout"),
                                                  health_check.get("check_interval"))
                gcp_health_check.gcp_cloud_project = cloud_project
                gcp_port_health_check = GcpPortHealthCheck(health_check.get('port'), health_check.get('request'),
                                                           health_check.get('response'),
                                                           health_check.get('proxy_header'))
                gcp_health_check.port_health_check = gcp_port_health_check
                objs_to_configure.append(gcp_health_check)
                doosradb.session.add(gcp_health_check)
                gcp_backend_service.health_check = gcp_health_check
            if not gcp_url_map.default_backend_service:
                gcp_url_map.default_backend_service = gcp_backend_service
            objs_to_configure.append(gcp_backend_service)
            doosradb.session.add(gcp_backend_service)
            backend_services_list.append(gcp_backend_service)
            gcp_load_balancer.backend_services.append(gcp_backend_service)

        if data.get('host_rules'):
            for host_rule in data.get('host_rules'):
                gcp_host_rule = GcpHostRule(host_rule.get('hosts'))
                gcp_path_matcher = GcpPathMatcher(PATH_MATCHER_NAME.format(load_balancer_name), "CREATED BY VPC+")
                for backend_service in backend_services_list:
                    if backend_service.name == host_rule.get('backend_service'):
                        gcp_path_matcher.default_backend_service = backend_service
                        break

                if len(data.get('backend_services')) > 1:
                    gcp_path_rule = GcpPathRule(host_rule.get('paths'))
                    gcp_path_rule.service = gcp_path_matcher.default_backend_service
                    gcp_path_matcher.path_rules.append(gcp_path_rule)
                gcp_host_rule.path_matcher = gcp_path_matcher
                gcp_url_map.host_rules.append(gcp_host_rule)

        objs_to_configure.append(gcp_url_map)
        for frontend in data.get('frontends'):
            existing_forwarding_rule = gcp_manager.compute_engine_operations.fetch_ops.get_forwarding_rules(
                cloud_project.project_id, name=frontend.get('name'))
            if existing_forwarding_rule:
                raise CloudInvalidRequestError("Forwarding Rule with name '{}' already exists".format(frontend['name']))
            gcp_forwarding_rule = GcpForwardingRule(frontend.get('name'), frontend.get('ip_address'),
                                                    frontend.get('protocol'), frontend.get('ip_version'),
                                                    frontend.get('port_range'), frontend.get('description'),
                                                    load_balancing_scheme="EXTERNAL", type_="GLOBAL")
            target_proxy = GcpTargetProxy(TARGET_PROXY_NAME.format(load_balancer_name), frontend.get('ip_protocol'),
                                          "CREATED BY VPC+")
            target_proxy.url_map = gcp_url_map
            objs_to_configure.append(target_proxy)
            gcp_forwarding_rule.target_proxy = target_proxy
            gcp_forwarding_rule.gcp_cloud_project = cloud_project
            objs_to_configure.append(gcp_forwarding_rule)
            doosradb.session.add(gcp_forwarding_rule)
            gcp_load_balancer.forwarding_rules.append(gcp_forwarding_rule)

        gcp_url_map.gcp_cloud_project = cloud_project
        doosradb.session.add(gcp_url_map)
        gcp_load_balancer.url_map = gcp_url_map
        doosradb.session.add(gcp_load_balancer)
        doosradb.session.commit()

        for obj in objs_to_configure:
            gcp_manager.compute_engine_operations.push_obj_confs(obj, cloud_project.project_id)
            obj.status = CREATED
            doosradb.session.commit()
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
        if gcp_load_balancer:
            gcp_load_balancer.status = ERROR_CREATING
            doosradb.session.commit()
        for obj in objs_to_configure:
            if not obj.status == CREATED:
                obj.status = ERROR_CREATING
                doosradb.session.commit()
        return None, ex.msg
    else:
        gcp_load_balancer.status = CREATED
        doosradb.session.commit()
        return gcp_load_balancer, None


def delete_load_balancer(load_balancer):
    """
    Delete load balancer from Google Cloud Platform
    :return:
    """
    objs_to_delete = list()
    cloud_project = load_balancer.gcp_cloud_project
    current_app.logger.info("Deleting Load Balancer '{name}' on cloud project '{project}'".format(
        name=load_balancer.name, project=cloud_project.name))
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        for forwarding_rule in load_balancer.forwarding_rules.all():
            existing_forwarding_rule = gcp_manager.compute_engine_operations.fetch_ops.get_forwarding_rules(
                cloud_project.project_id, forwarding_rule.name)
            if existing_forwarding_rule:
                objs_to_delete.append(forwarding_rule)
            if forwarding_rule.target_proxy:
                existing_target_proxy = gcp_manager.compute_engine_operations.fetch_ops.get_target_proxies(
                    cloud_project.project_id, "HTTP", forwarding_rule.target_proxy.name)
                if existing_target_proxy:
                    objs_to_delete.append(forwarding_rule.target_proxy)

        if load_balancer.url_map:
            url_map = load_balancer.url_map
            existing_url_map = gcp_manager.compute_engine_operations.fetch_ops.get_url_maps(
                cloud_project.project_id, url_map.name)
            if existing_url_map:
                objs_to_delete.append(url_map)
        doosradb.session.commit()

        for backend_service in load_balancer.backend_services.all():
            existing_backend_service = gcp_manager.compute_engine_operations.fetch_ops.get_backend_services(
                cloud_project.project_id, backend_service.name)
            if existing_backend_service:
                objs_to_delete.append(backend_service)
            if backend_service.health_check:
                existing_health_check = gcp_manager.compute_engine_operations.fetch_ops.get_health_checks(
                    cloud_project.project_id, backend_service.health_check.name)
                if existing_health_check:
                    objs_to_delete.append(backend_service.health_check)
        for obj in objs_to_delete:
            obj.status = DELETING
            doosradb.session.commit()
            gcp_manager.compute_engine_operations.push_obj_confs(obj, cloud_project.project_id, delete=True)
            obj.status = DELETED
            doosradb.session.commit()
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
        load_balancer.status = ERROR_DELETING
        doosradb.session.commit()
        return False, ex.msg
    else:
        load_balancer.status = DELETED
        doosradb.session.delete(load_balancer)
        doosradb.session.commit()
        return True, None
