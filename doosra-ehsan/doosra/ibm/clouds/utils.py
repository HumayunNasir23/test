import datetime
import hashlib
import hmac

import requests
from flask import current_app

from doosra import db as doosradb
from doosra.common.utils import decrypt_api_key
from doosra.ibm.clouds.consts import INVALID, VALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMCloud, IBMCredentials


def verify_cloud_credentials(cloud):
    """
    Verify IBM cloud credentials and save the credentials to database
    """
    try:
        hmac = True
        resource_group_names = []
        ibm_manager = IBMManager(cloud)
        cloud.credentials = IBMCredentials(ibm_manager.iam_ops.authenticate_cloud_account())
        if cloud.service_credentials:
            ibm_manager.cos_ops.fetch_ops.get_buckets()
            resource_groups = ibm_manager.resource_ops.raw_fetch_ops.get_resource_groups()
            resource_group_names = [resource_group["name"] for resource_group in resource_groups]
        if cloud.service_credentials.access_key_id and cloud.service_credentials.secret_access_key:
            hmac = validate_hmac(decrypt_api_key(cloud.service_credentials.access_key_id),
                                 decrypt_api_key(cloud.service_credentials.secret_access_key))
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        cloud.status = INVALID
        doosradb.session.commit()
    else:
        if len(resource_group_names) != len(set(resource_group_names)):
            cloud.status = IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS
        else:
            cloud.status = VALID
        if not hmac:
            cloud.status = INVALID
        doosradb.session.commit()


def hash(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def create_signature_key(key, datestamp, service):
    key_date = hash(('AWS4' + key).encode('utf-8'), datestamp)
    key_string = hash(key_date, '')
    key_service = hash(key_string, service)
    key_signing = hash(key_service, 'aws4_request')
    return key_signing


def hmac_request(host, endpoint, secret_key, access_key):
    time = datetime.datetime.utcnow()
    timestamp = time.strftime('%Y%m%dT%H%M%SZ')
    datestamp = time.strftime('%Y%m%d')

    standardized_resource = '/'
    standardized_querystring = ''
    standardized_headers = 'host:' + host + '\n' + 'x-amz-date:' + timestamp + '\n'
    signed_headers = 'host;x-amz-date'
    payload_hash = hashlib.sha256(''.encode('utf-8')).hexdigest()

    standardized_request = ('GET' + '\n' +
                            standardized_resource + '\n' +
                            standardized_querystring + '\n' +
                            standardized_headers + '\n' +
                            signed_headers + '\n' +
                            payload_hash).encode('utf-8')

    # assemble string-to-sign
    hashing_algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = datestamp + '/' + '/' + 's3' + '/' + 'aws4_request'
    sts = (hashing_algorithm + '\n' +
           timestamp + '\n' +
           credential_scope + '\n' +
           hashlib.sha256(standardized_request).hexdigest())

    # generate the signature
    signature_key = create_signature_key(secret_key, datestamp, 's3')
    signature = hmac.new(signature_key,
                         (sts).encode('utf-8'),
                         hashlib.sha256).hexdigest()

    # assemble all elements into the 'authorization' header
    v4auth_header = (hashing_algorithm + ' ' +
                     'Credential=' + access_key + '/' + credential_scope + ', ' +
                     'SignedHeaders=' + signed_headers + ', ' +
                     'Signature=' + signature)

    headers = {'x-amz-date': timestamp, 'Authorization': v4auth_header}
    request_url = endpoint + standardized_resource + standardized_querystring
    request = requests.get(request_url, headers=headers)

    return request.status_code


def validate_hmac(access_key, secret_key):
    host = 's3.{region}.cloud-object-storage.appdomain.cloud'
    regions = ['eu', 'ap', 'us']
    resp = []
    for region in regions:
        host = host.format(region=region)
        resp.append(hmac_request(host, 'https://' + host, secret_key, access_key))
    if 200 in resp:
        return True
    else:
        return False
