import json

from flask import current_app, jsonify, request, Response
from sqlalchemy import or_

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.models import Template
from doosra.validate_json import validate_json
from doosra.vpc_templates import ibm_templates
from doosra.vpc_templates.consts import PRE_DEFINED_TEMPLATE
from doosra.vpc_templates.schemas import *


@ibm_templates.route('/templates', methods=['POST'])
@validate_json(add_template_schema)
@authenticate
def add_vpc_template(user_id, user):
    """
    Add VPC template
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    data = request.get_json(force=True)
    existing_template = doosradb.session.query(Template).filter_by(
        name=data["name"], project_id=user.project.id).first()
    if existing_template:
        return Response("ERROR_CONFLICTING_TEMPLATE_NAME", status=409)

    template = Template(
        data["name"], data["schema"], data["schema_type"], data["cloud_type"], data.get("description"), user.project.id)
    doosradb.session.add(template)
    doosradb.session.commit()

    return Response(json.dumps(template.to_json()), status=201, mimetype="application/json")


@ibm_templates.route('/templates', methods=['GET'])
@authenticate
def get_templates(user_id, user):
    """
    Get VPC templates
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    templates_list = list()

    templates = doosradb.session.query(Template).filter(or_(
        Template.project_id == user.project.id, Template.type == PRE_DEFINED_TEMPLATE)).all()

    if not templates:
        current_app.logger.info("No templates found for project with ID {}".format(user.project.id))
        return Response(status=204)

    for template in templates:
        templates_list.append(template.to_json())

    return Response(json.dumps(templates_list), mimetype='application/json')


@ibm_templates.route('/templates/<template_id>', methods=['GET'])
@authenticate
def get_template(user_id, user, template_id):
    """
    Get a vpc template provided its template_id
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    template = doosradb.session.query(Template).filter_by(id=template_id, project_id=user.project.id).first()
    if not template:
        current_app.logger.info("No Template found with ID {template_id}".format(template_id=template_id))
        return Response(status=204)

    return Response(json.dumps(template.to_json()), mimetype='application/json')


@ibm_templates.route('/templates/<template_id>', methods=['DELETE'])
@authenticate
def delete_template(user_id, user, template_id):
    """
    Delete a VPC template provided its template_id
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    template = doosradb.session.query(Template).filter_by(id=template_id, project_id=user.project.id).first()
    if not template:
        current_app.logger.info("No Template found with ID {template_id}".format(template_id=template_id))
        return Response(status=404)

    if template.is_pre_built:
        current_app.logger.info(
            "Pre-built template with ID {template_id} cannot be deleted".format(template_id=template_id))
        return Response(status=400)

    doosradb.session.delete(template)
    doosradb.session.commit()
    return Response(status=204)


@ibm_templates.route('/templates/<template_id>', methods=['PATCH'])
@authenticate
@validate_json(update_template_schema)
def update_template(user_id, user, template_id):
    """
    Update a template
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param template_id: template_id for Template object
    :return: Response object from flask package
    """
    data = request.get_json(force=True)

    template = doosradb.session.query(Template).filter_by(id=template_id, project_id=user.project.id).first()
    if not template:
        current_app.logger.info("No Template found with ID {}".format(template_id))
        return Response(status=404)

    if data.get("name") and data["name"] != template.name:
        existing_template = doosradb.session.query(Template).filter_by(
            name=data["name"], project_id=user.project.id).first()
        if existing_template:
            return Response("ERROR_SAME_NAME", status=409)

        template.name = data["name"]
        doosradb.session.commit()

    template.api_key = data["description"] if data.get('description') else template.api_key
    template.api_key = data["cloud_type"] if data.get('cloud_type') else template.cloud_type
    template.api_key = data["schema_type"] if data.get('schema_type') else template.schema_type
    template.api_key = data["schema"] if data.get('schema') else template.schema
    doosradb.session.commit()

    return jsonify(template.to_json())
