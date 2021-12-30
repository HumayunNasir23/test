from functools import wraps
import requests

from flask import request, Response

from doosra import db as doosradb
from doosra.common.consts import AUTH_LINK
from doosra.models.users_models import Project, User

def authenticate(func):
    """Validate token."""

    @wraps(func)
    def authenticate_and_call(*args, **kwargs):
        auth_header = request.headers.get('Authorization', type=str)
        if not auth_header:
            return Response(status=401)

        split_auth_header = auth_header.split()
        if not len(split_auth_header) == 2:
            return Response(status=401)

        token = split_auth_header[1]
        resp = requests.get(url=AUTH_LINK, headers={'Authorization': f"Bearer {token}"})
        if not resp or resp.status_code != 200:
            return Response(status=401)

        resp_json = resp.json()
        user = doosradb.session.query(User).filter_by(id=resp_json['id']).first()
        if not user:
            user = User(_id=resp_json['id'], email=resp_json['email'])
            user.project = Project(resp_json['project_id'])
            doosradb.session.add(user)
            doosradb.session.commit()

        kwargs['user'] = user
        kwargs['user_id'] = user.id
        return func(*args, **kwargs)

    return authenticate_and_call