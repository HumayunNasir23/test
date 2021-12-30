import os

EXPIRY = 2  # hours
VPCPLUS_LINK = os.environ.get('VPCPLUS_LINK', 'https://vpc.wanclouds.net/')
REGISTER_URL = VPCPLUS_LINK + "register"
SHARE_EMAIL_SUBJECT = "[VPC+] Account shared"
LOGIN_URL = VPCPLUS_LINK + "login"
CONFIRM_EMAIL_SUBJECT = "Confirm your VPC+ account"
APPROVE_NEW_USER_SUBJECT = "Approve new VPC+ user"
LOGIN_EMAIL_SUBJECT = "Login to your VPC+ account"
RESET_PASSWORD_SUBJECT = "[VPC+] Reset password instructions"
PASSWORD_CHANGED_SUBJECT = "[VPC+] Your password has changed"
INVALID_EMAIL = "ERROR_INVALID_EMAIL: '{}'"
INVALID_USER = "ERROR_INVALID_USER: '{}'"
INVALID_PASSWORD = "ERROR_INVALID_PASSWORD: '{}'"
EMAIL_NOT_CONFIRMED = "ERROR_EMAIL_NOT_CONFIRMED: '{}'"
ERROR_ACCOUNT_NOT_APPROVED = "ERROR_ACCOUNT_NOT_APPROVED: '{}'"
ERROR_ALREADY_CONFIRMED = "ERROR_ALREADY_CONFIRMED: '{}'"
ERROR_INVALID_TOKEN = "ERROR_INVALID_TOKEN: '{}'"
ERROR_USED_TOKEN = "ERROR_USED_TOKEN"
INVITE_EMAIL_SUBJECT = "Invitation to VPC+"

ERROR_TOO_MANY_ATTEMPTS_ON_PIN = "Too many login attempts, please request for a new pin"
ERROR_MESSAGE_ACCOUNT_NOT_APPROVED = "Account is waiting for approval by admin"
ERROR_MESSAGE_EMAIL_NOT_CONFIRMED = "The provided email address has not been confirmed yet. " \
                                    "Please check your email to confirm this account."

MAX_PREVIOUS_PASSWORDS = 5
VPCPLUS = "VPC_PLUS"
IBM = "IBM"
