import requests

from flask import current_app
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None):
    method_whitelist = ["GET", "PUT", "POST", "DELETE"]
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        method_whitelist=method_whitelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def make_request(method, url, data=None, headers=None, auth=None, params=None, timeout=10):
    """ Make a request to the provided url and return the response

    :param method: "POST", "PUT", "DELETE", "PATCH", "GET"
    :param url: e.g "http://abcdefg.com/api"
    :param data: e.g {"key": value}
    :param headers: e.g {"accept": application/json}
    :param auth: (username, password)
    :param params: dictionary or bytes to be sent in the query
    :param timeout: timeout for requests(server should start sending response within this time)
    :return: Boolean
    """
    try:
        return requests_retry_session().request(
            method, url, data=data, headers=headers, auth=auth, params=params, timeout=timeout, verify=False)
    except requests.exceptions.RequestException as e:
        current_app.logger.error(e)
        return
