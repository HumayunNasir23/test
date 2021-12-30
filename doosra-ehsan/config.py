import os
import requests
from datetime import timedelta

BASEDIR = os.path.abspath(os.path.dirname(__file__))
from celery.schedules import crontab


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "my_precious_doosra")
    SECURITY_PASSWORD_SALT = "my_precious_doosra_two"
    LOKI_LOGGING = False
    SLACK_LOGGING = False
    ADMIN_APPROVAL_REQUIRED = True if os.environ.get("ADMIN_APPROVAL_REQUIRED") == "True" else False

    # Encryption configs
    SALT_LENGTH = 32
    DERIVATION_ROUNDS = 100000
    BLOCK_SIZE = 16
    KEY_SIZE = 32
    SECRET = "nw2FrNshF"

    # Pagination Configs
    DOOSRA_DEFAULT_PAGE_LIMIT = 10
    DOOSRA_MAX_PAGE_LIMIT = 50

    # Logging configs
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s [%(lineno)s]: %(message)s"
            }
        },
        "root": {"level": "INFO", "handlers": ["gunicorn"]},
        "handlers": {
            "gunicorn": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            }
        },
    }

    # JWT configs
    JWT_ACCESS_TOKEN_EXPIRES = 432000
    JWT_SECRET_KEY = os.environ.get("SECRET_KEY", "my_precious_doosra")
    MAX_PIN_ATTEMPTS = 3
    PIN_LENGTH = 6
    PIN_EXPIRY = 900
    JWT_CUSTOM_EXPIRES = 2  # days
    JWT_PASSWORD_RESET_LINK_EXPIRES = 15  # 15min
    JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDsiwKQghU2YJEE0az/QgXmfSBV
0NIThW40QsdfzABwVv++o3SIeMWZ1qWJ93d9ConXWxlkNxXWXyVFV0e7F0kVZpKu
QAJReZ4qokYm9koNXKGxQcqY8eSbS5EGiqJXYFmWJqeDgHukV6HzGjd//CXsBdZj
+BzcPyl9SHOPYbsrjwIDAQAB
-----END PUBLIC KEY-----"""
    JWT_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDsiwKQghU2YJEE0az/QgXmfSBV0NIThW40QsdfzABwVv++o3SI
eMWZ1qWJ93d9ConXWxlkNxXWXyVFV0e7F0kVZpKuQAJReZ4qokYm9koNXKGxQcqY
8eSbS5EGiqJXYFmWJqeDgHukV6HzGjd//CXsBdZj+BzcPyl9SHOPYbsrjwIDAQAB
AoGABtUZFN19CV4OsknwKktY6khw96mZd9Dh1waaxayZ0qTgrDwCcLK0WnY1v99z
BxyX0K2j9R4WNmP3KqKTwtawWKyuVP4kfwfLu9hV3MRrh0gEj93jYCxGK8KKRPl8
ybnUx/8e7HvNLzPmr0skoupiGaU37Mn//9OeDyn0lF05C3kCQQD8dIVQQxreHWg4
VWMvtUBrnIhhuTN7uotzt+8Vln+nLDWxykEaB4tu4uYoioPu/6JtEvCILWmtgHh3
NlMp76P9AkEA791Ki735CTXjRD/dBscl/M6KUaH0UTLY+g77Fzmok+tFJvrLS5Yt
DDFu4KVEq4H5Frm2hiR7rnsRhwejkHQ1ewJBAK5fgVGN+DnhEAKRIABs7kEmDqGJ
PYFBuV7FdjNwD14V0ESsUck72thNivIHstda5QL36QH2dB7uNMcK0+iMaLUCQFla
2JBiPsmdl4IvQElsGsyorIJokLlG9emBdyxZwGEKPgKdXupTkYh/SczKBGDX1FEQ
8dva73A6THc+80G26M0CQBLDC4XaFxyCAKcCZhUffwaCDObVjV1ML6YvHVzqvfKh
nCxLs3llTCZYMHHkOr7BZ6Zpywc73YMilzXBXK9c7DI=
-----END RSA PRIVATE KEY-----"""

    # GCP configs
    CLIENT_SECRETS_FILE = BASEDIR + "/client_secret.json"
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

    DOOSRA_DBPARAMS = {
        "WEBDB_ENV_MYSQL_DB_HOST": os.environ.get("WEBDB_ENV_MYSQL_DB_HOST", "webdb"),
        "WEBDB_ENV_MYSQL_PORT": os.environ.get("WEBDB_ENV_MYSQL_PORT", "3306"),
        "WEBDB_ENV_MYSQL_DATABASE": os.environ.get(
            "WEBDB_ENV_MYSQL_DATABASE", "doosradb"
        ),
        "WEBDB_ENV_MYSQL_USER": os.environ.get("WEBDB_ENV_MYSQL_USER", "root"),
        "WEBDB_ENV_MYSQL_PASSWORD": os.environ.get(
            "WEBDB_ENV_MYSQL_PASSWORD", "admin123"
        ),
    }
    DOOSRA_RABBITPARAMS = {
        "RABBIT_ENV_RABBITMQ_USER": os.environ.get(
            "RABBIT_ENV_RABBITMQ_USER", "doosra"
        ),
        "RABBIT_ENV_RABBITMQ_PASSWORD": os.environ.get(
            "RABBIT_ENV_RABBITMQ_PASSWORD", "a48256de-b999-44c4-8ac2-372fb099bca1"
        ),
    }
    REDIS_PARAMS = {
        "PORT": int(os.environ.get("REDIS_PORT") or 6379),
        "PASSWORD": os.environ.get("REDIS_PASSWORD", "admin123"),
        "HOST": os.environ.get("REDIS", "redis"),
        "DB": os.environ.get("REDIS_DB", 0),
    }
    CELERY_RESULT_BACKEND = "redis://:{PASSWORD}@{HOST}:{PORT}/{DB}".format(
        **REDIS_PARAMS
    )
    CELERY_BROKER_URL = "amqp://{RABBIT_ENV_RABBITMQ_USER}:{RABBIT_ENV_RABBITMQ_PASSWORD}@rabbitmq:5672//".format(
        **DOOSRA_RABBITPARAMS
    )
    # Default two hours set by flask sqlalchemy

    # Not 4 hours in case of workers whic good workaround need to be restored
    # after blocking removed default is 5 mins
    SQLALCHEMY_POOL_RECYCLE = int(os.environ.get("SQLALCHEMY_POOL_RECYCLE", "400"))
    SQLALCHEMY_POOL_TIMEOUT = int(os.environ.get("SQLALCHEMY_POOL_TIMEOUT", "450"))
    SQLALCHEMY_POOL_SIZE = int(os.environ.get("SQLALCHEMY_POOL_SIZE", "20"))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get("SQLALCHEMY_MAX_OVERFLOW", "0"))
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": SQLALCHEMY_POOL_RECYCLE,
        "pool_timeout": SQLALCHEMY_POOL_TIMEOUT,
        "pool_size": SQLALCHEMY_POOL_SIZE,
        "max_overflow": SQLALCHEMY_MAX_OVERFLOW
    }

    # Should be 1 in case of prefork worker to make sure one process is consuming one connection
    # default is 5
    SQLALCHEMY_DATABASE_URI = (
        "mysql+mysqldb://{WEBDB_ENV_MYSQL_USER}:{WEBDB_ENV_MYSQL_PASSWORD}@"
        "{WEBDB_ENV_MYSQL_DB_HOST}:{WEBDB_ENV_MYSQL_PORT}/"
        "{WEBDB_ENV_MYSQL_DATABASE}".format(**DOOSRA_DBPARAMS)
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PRESERVE_CONTEXT_ON_EXCEPTION = False

    # mail settings
    MAIL_SERVER = "smtp.googlemail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    # slack settings
    SLACK_WEBHOOK_URL = os.environ.get(
        'SLACK_WEBHOOK_URL', 'https://hooks.slack.com/services/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')
    SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#vpc_bleeding_channel')

    # gmail authentication
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "noreply@wanclouds.net")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "mywanclouds1234")

    # mail accounts
    MAIL_DEFAULT_SENDER = "noreply@wanclouds.net"

    # celery optimizations
    BROKER_POOL_LIMIT = int(os.environ.get("BROKER_POOL_LIMIT", "1"))  # Will decrease connection usage
    BROKER_HEARTBEAT = None  # We're using TCP keep-alive instead
    BROKER_CONNECTION_TIMEOUT = int(os.environ.get("BROKER_CONNECTION_TIMEOUT", "30"))
    # May require a long timeout due to Linux DNS timeouts etc

    CELERY_SEND_EVENTS = False  # Will not create celeryev.* queues
    CELERY_EVENT_QUEUE_EXPIRES = (
        60
    )  # Will delete all celeryev. queues without consumers after 1 minute.

    # celery settings
    ack_late = os.environ.get("CELERY_ACKS_LATE", "True")
    CELERY_ACKS_LATE = ack_late in {"TRUE", "True", "true", "YES", "Yes", "yes", "1"}
    CELERYD_MAX_TASKS_PER_CHILD = int(os.environ.get("MAX_TASKS_PER_CHILD", "1"))
    CELERYD_PREFETCH_MULTIPLIER = int(os.environ.get("PREFETCH_MULTIPLIER", "1"))
    CELERY_TASK_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "UTC"

    CELERYBEAT_SCHEDULE = {
        "delete_older_tasks": {
            "task": "delete_older_tasks",
            "schedule": crontab(minute=0, hour=0),
        },
        "delete_ibm_clouds": {
            "task": "delete_ibm_clouds",
            "schedule": timedelta(hours=2)
        },
        'run_sync': {
            "task": "initiate_sync",
            "schedule": timedelta(minutes=5),
            'options': {'queue': 'beat_queue'}
        },
        'run_ic_task_distributor': {
            "task": "ic_task_distributor",
            "schedule": timedelta(seconds=30),
            'options': {'queue': 'image_conversion_queue'}
        },
        'run_ic_instances_overseer': {
            "task": "ic_instances_overseer",
            "schedule": timedelta(seconds=40),
            'options': {'queue': 'image_conversion_queue'}
        },
        'run_ic_pending_task_executor': {
            "task": "ic_pending_task_executor",
            "schedule": timedelta(minutes=1),
            'options': {'queue': 'image_conversion_queue'}
        },
        "run_instance_tasks": {
            "task": "complete_instance_tasks",
            "schedule": timedelta(minutes=1),
        },
        "run_load_balancers_tasks": {
            "task": "initiate_load_balancer_provisioning",
            "schedule": timedelta(minutes=1),
        }
        #"run_workflow_manager": {
        #    "task": "workflow_manager",
        #    "schedule": 3.0,
        #}
    }

    # File upload setting
    MAX_CONTENT_LENGTH = 2048 * 2048

    # IBM VPC Generation Settings
    GENERATION = os.environ.get('GENERATION', '2')

    # Compress settings
    COMPRESS_MIMETYPES = ["application/json"]
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500

    # DB Migration Controller settings
    DB_MIGRATION_API_KEY = os.environ.get('DB_MIGRATION_API_KEY', 'abc123!')
    DB_MIGRATION_CONTROLLER_HOST = os.environ.get('DB_MIGRATION_CONTROLLER_HOST',
                                                  'https://db-migration-engg.wanclouds.net')
    DB_MIGRATION_INSTANCE_TYPE = os.environ.get("DB_MIGRATION_INSTANCE_TYPE", "vpc-engg")

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    PORT = 8081
    USE_SSL = os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


class ProductionConfig(Config):
    DEBUG = False

    LOKI_LOGGING = True if os.environ.get("LOKI_LOGGING") == "enabled" else False
    LOKI_URL = os.environ.get("LOKI_URL")
    LOKI_USERNAME = os.environ.get("LOKI_USERNAME", "admin")
    LOKI_PASSWORD = os.environ.get("LOKI_PASSWORD", "admin")
    slack_response = requests.get(Config.SLACK_WEBHOOK_URL)
    SLACK_LOGGING = True if os.environ.get("SLACK_LOGGING") == "enabled" and slack_response != 403 else False

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        import logging
        import urllib
        # Log to docker logs
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)

        # Error log to slack
        if cls.slack_response == 403:
            app.logger.info("****** Slack webhook is not correct ***********")
        else:
            if cls.SLACK_LOGGING:
                try:
                    from slack_log_handler import SlackLogHandler
                    slack_handler = SlackLogHandler(webhook_url=cls.SLACK_WEBHOOK_URL, channel=cls.SLACK_CHANNEL,
                                                    format='%(levelname)s - %(asctime)s - %(name)s - %(message)s')
                    slack_handler.setLevel(logging.ERROR)
                    app.logger.addHandler(slack_handler)
                except urllib.error.HTTPError:
                    app.logger.info("******************** Slack webhook is not working ******************")
        # Log to loki server
        if cls.LOKI_LOGGING:
            import logging_loki
            tag = os.environ.get('TAGS')
            try:
                handler = logging_loki.LokiHandler(
                    url="{0}/loki/api/v1/push".format(cls.LOKI_URL),
                    tags={"application": tag},
                    auth=(cls.LOKI_USERNAME, cls.LOKI_PASSWORD),
                    version="1",

                )
                app.logger.setLevel(logging.INFO)
                app.logger.addHandler(handler)
            except:
                pass


class TestingConfig(Config):
    pass


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    # Local server uses default config
    "default": DevelopmentConfig,
}
