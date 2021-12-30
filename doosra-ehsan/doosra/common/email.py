"""Send email"""

from flask_mail import Message

from config import config
from doosra import mail
from doosra.common.celery_app import create_celery_app
from doosra.tasks.celery_app import app, initialize_loki, initialize_slack_logger

celery = create_celery_app()

if app.config["LOKI_LOGGING"]:
    from celery.signals import after_setup_logger

    after_setup_logger.connect(initialize_loki)

if app.config["SLACK_LOGGING"]:
    from celery.signals import after_setup_logger

    after_setup_logger.connect(initialize_slack_logger)


@celery.task(name="send_email")
def send_email(to, subject, template):
    """Send email"""
    recipients = [to] if isinstance(to, str) else to
    msg = Message(subject, recipients=recipients, html=template, sender=config['default'].MAIL_DEFAULT_SENDER)
    mail.send(msg)
