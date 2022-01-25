from ibm_cloud_sdk_core.authenticators.iam_authenticator import IAMAuthenticator
from ibm_secrets_manager_sdk.secrets_manager_v1 import *
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY=os.getenv('API_KEY')
SECRET_MANAGER_URL=os.getenv('SECRET_MANAGER_URL')
secretsManager = SecretsManagerV1(
    authenticator=IAMAuthenticator(apikey=API_KEY)
)

secretsManager.set_service_url(SECRET_MANAGER_URL)

SECRET_KEY = secretsManager.get_secret(
'arbitrary',
'9b1fdd2c-d90f-fd05-9880-05fe66ad7e50')
print(SECRET_KEY)
print(SECRET_KEY.result['resources'][0]['secret_data'])

DOOSRA_RABBITPARAMS = secretsManager.get_secret(
'username_password',
'0378402d-a78c-b1d6-9df1-f80c62e17b4c')
print(DOOSRA_RABBITPARAMS.result['resources'][0]['secret_data'])

MAIL = secretsManager.get_secret(
'username_password',
'26ccea58-8153-f41d-676f-3b14f90d81f0')
print(MAIL.result['resources'][0]['secret_data'])

MAIL_SERVER = secretsManager.get_secret(
'arbitrary',
'4ae90f79-afde-aee6-1520-ef8deea80992')
print(MAIL_SERVER.result['resources'][0]['secret_data'])

SLACK_WEBHOOK_URL = secretsManager.get_secret(
'arbitrary',
'dc1a9e85-0c5b-2322-6c4e-04f499098e6f')
print(SLACK_WEBHOOK_URL.result['resources'][0]['secret_data'])

SLACK_CHANNEL = secretsManager.get_secret(
'arbitrary',
'1c439c18-eeab-a863-ed74-da85d90127e5')
print(SLACK_CHANNEL.result['resources'][0]['secret_data'])

SECRET = secretsManager.get_secret(
'arbitrary',
'715d1bc5-8947-9721-01db-fab9653e4367')
print(SECRET.result['resources'][0]['secret_data'])

LOKI = secretsManager.get_secret(
'username_password',
'5c174317-7c73-2d79-0d84-19ac31fa4bcd')
print(LOKI.result['resources'][0]['secret_data'])

DOOSRA_DBPARAMS = secretsManager.get_secret(
'username_password',
'6a8c710c-ba55-f8a7-e519-55ded25a517d')
print(DOOSRA_DBPARAMS.result['resources'][0]['secret_data'])

SECURITY_PASSWORD_SALT = secretsManager.get_secret(
'arbitrary',
'839693f4-50d0-e3b3-5910-d1c0d1b17048')
print(SECURITY_PASSWORD_SALT.result['resources'][0]['secret_data'])

DB_MIGRATION_API_KEY = secretsManager.get_secret(
'arbitrary',
'f1058e82-886b-b83a-da24-eaa07239ddd5')
print(DB_MIGRATION_API_KEY.result['resources'][0]['secret_data'])

REDIS_PARAMS = secretsManager.get_secret(
'username_password',
'a785b2a1-c4ae-231d-1fb1-ceeb283521c8')
print(REDIS_PARAMS.result['resources'][0]['secret_data'])

JWT_PUBLIC_KEY = secretsManager.get_secret(
'arbitrary',
'48b2621a-9487-dd91-598c-c8731d72582d')
print(JWT_PUBLIC_KEY.result['resources'][0]['secret_data'])

JWT_PRIVATE_KEY = secretsManager.get_secret(
'arbitrary',
'615a85b9-f883-da18-d51c-7f810566a509')
print(JWT_PRIVATE_KEY.result['resources'][0]['secret_data'])
