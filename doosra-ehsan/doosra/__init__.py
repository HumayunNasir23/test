from logging.config import dictConfig

from flask import Flask
from flask_compress import Compress
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy as _BaseSQLAlchemy

from config import config


class SQLAlchemy(_BaseSQLAlchemy):
    def apply_pool_defaults(self, app, options):
        super().apply_pool_defaults(app, options)
        options["pool_pre_ping"] = True

compress = Compress()
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    compress.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    jwt.init_app(app)
    db.app = app

    if app.config.get("DEBUG"):
        app.config["LOGGING_CONFIG"]["root"]["level"] = "DEBUG"
    dictConfig(app.config["LOGGING_CONFIG"])

    from doosra.db_migration import db_migration as db_migration_blueprint
    from doosra.users import users as users_blueprint
    from doosra.gcp.clouds import gcp_clouds as gcp_clouds_blueprint
    from doosra.gcp.common import gcp as gcp_blueprint
    from doosra.gcp.firewalls import gcp_firewalls as gcp_firewalls_blueprint
    from doosra.gcp.instance_groups import (
        gcp_instance_groups as gcp_instance_groups_blueprint,
    )
    from doosra.gcp.load_balancers import (
        gcp_load_balancers as gcp_load_balancers_blueprint,
    )
    from doosra.gcp.vpc import gcp_vpc as gcp_vpc_blueprint
    from doosra.gcp.instance import gcp_instance as gcp_instance_blueprint
    from doosra.ibm.acls import ibm_acls as ibm_acls_blueprint
    from doosra.ibm.clouds import ibm_clouds as ibm_clouds_blueprint
    from doosra.ibm.common import ibm_common as ibm_common_blueprint
    from doosra.ibm.instances import ibm_instances as ibm_instances_blueprint
    from doosra.ibm.load_balancers import (
        ibm_load_balancers as ibm_load_balancers_blueprint,
    )
    from doosra.ibm.public_gateways import (
        ibm_public_gateways as ibm_public_gateways_blueprint,
    )
    from doosra.ibm.security_groups import (
        ibm_security_groups as ibm_security_groups_blueprint,
    )
    from doosra.ibm.vpcs import ibm_vpcs as ibm_vpcs_blueprint
    from doosra.ibm.vpns import ibm_vpns as ibm_vpns_blueprint
    from doosra.ibm.ssh_keys import ibm_ssh_keys as ibm_ssh_keys_blueprint
    from doosra.ibm.images import ibm_images as ibm_images_blueprint
    from doosra.ibm.floating_ips import ibm_floating_ips as ibm_floating_ips_blueprint
    from doosra.migration import migration as migration_blueprint
    from doosra.softlayer import softlayer as softlayer_blueprint
    from doosra.vpc_templates import ibm_templates as ibm_templates_blueprint
    from doosra.transit_gateway import transit_gateway as transit_gateway_blueprint
    from doosra.transit_gateway.common import transit_common as transit_common_blueprint
    from doosra.ibm.kubernetes import ibm_k8s as ibm_k8s_blueprint
    from doosra.ibm.dedicated_hosts import ibm_dedicated_hosts as ibm_dedicated_hosts_blueprint
    from doosra.workflows import ibm_workflows as ibm_workflows_blueprint

    app.register_blueprint(db_migration_blueprint, url_prefix="/v1/db_migration/proxy")
    app.register_blueprint(users_blueprint, url_prefix="/v1")
    app.register_blueprint(gcp_blueprint, url_prefix="/v1/gcp")
    app.register_blueprint(gcp_clouds_blueprint, url_prefix="/v1/gcp")
    app.register_blueprint(gcp_firewalls_blueprint, url_prefix="/v1/gcp")
    app.register_blueprint(gcp_instance_groups_blueprint, url_prefix="/v1/gcp")
    app.register_blueprint(gcp_load_balancers_blueprint, url_prefix="/v1/gcp")
    app.register_blueprint(gcp_vpc_blueprint, url_prefix="/v1/gcp")
    app.register_blueprint(gcp_instance_blueprint, url_prefix="/v1/gcp")
    app.register_blueprint(ibm_acls_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_clouds_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_common_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_instances_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_load_balancers_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_public_gateways_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_security_groups_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_vpcs_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_vpns_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_ssh_keys_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_images_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_floating_ips_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(migration_blueprint, url_prefix="/v1")
    app.register_blueprint(softlayer_blueprint, url_prefix="/v1/softlayer")
    app.register_blueprint(transit_gateway_blueprint, url_prefix="/v1")
    app.register_blueprint(transit_common_blueprint, url_prefix="/v1")
    app.register_blueprint(ibm_templates_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_k8s_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_dedicated_hosts_blueprint, url_prefix="/v1/ibm")
    app.register_blueprint(ibm_workflows_blueprint, url_prefix="/v1/ibm")

    return app
