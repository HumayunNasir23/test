import logging
from json import JSONDecodeError

import requests
from flask import jsonify, request, Response

from doosra.auth import authenticate
from doosra.db_migration import db_migration
from doosra.db_migration.consts import DB_MIGRATION_API_KEY, DB_MIGRATION_URL, REQUEST_TIMEOUT

LOGGER = logging.getLogger(__name__)


@db_migration.route("/<path:url>", methods=["GET", "DELETE", "POST", "PATCH"])
@authenticate
def proxy_requests_to_db_mig_controller(url, user_id, user):
    try:
        headers = {'S-API-Key': DB_MIGRATION_API_KEY}
        if request.method == "GET":
            request_args = dict(request.args)
            request_args['user_id'] = user_id
            resp_obj = requests.get(url=DB_MIGRATION_URL + url, headers=headers, params=request_args,
                                    timeout=REQUEST_TIMEOUT)

        elif request.method == "POST":
            payload = request.get_json(force=True)
            payload['user_id'] = user_id
            resp_obj = requests.post(url=DB_MIGRATION_URL + url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)

        elif request.method == "PATCH":
            payload = request.get_json()
            resp_obj = requests.patch(url=DB_MIGRATION_URL + url, headers=headers, json=payload if payload else {},
                                      timeout=REQUEST_TIMEOUT)

    except requests.exceptions.ConnectionError as ex:
        LOGGER.info(ex)
        return Response("DB MIGRATION SERVICE NOT AVAILABLE", 503)

    if not resp_obj.status_code in [200, 201]:
        return Response(status=resp_obj.status_code)

    try:
        resp_json = resp_obj.json()
    except JSONDecodeError:
        return Response("DB MIGRATION SERVICE NOT AVAILABLE", 503)

    return jsonify(resp_json), resp_obj.status_code
