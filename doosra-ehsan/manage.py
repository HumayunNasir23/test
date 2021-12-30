"""
Helper script for running flask server and perform DB migrations
"""
import json
import os

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Server, Shell

from doosra import create_app, db, models
from doosra.vpc_templates.consts import PRE_DEFINED_TEMPLATE
from doosra.vpc_templates.utils import load_json_templates

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, models=models)


def create_predefined_templates():
    json_templates = load_json_templates()
    templates = models.Template.query.filter_by(type=PRE_DEFINED_TEMPLATE).all()
    for template in json_templates:
        existing_template = None
        for template_ in templates:
            if template_.name == template['name']:
                existing_template = template_
                break

        if not existing_template:
            db.session.add(models.Template(
                template['name'], json.dumps(template['schema']), template['schema_type'], template['cloud_type'],
                template['description'], type_=PRE_DEFINED_TEMPLATE))
            db.session.commit()

        else:
            existing_template.schema = json.dumps(template['schema'])
            db.session.commit()


port = os.getenv('PORT', '8081')
manager.add_command("runserver", Server(host="0.0.0.0", port=int(port)))
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def pre_reqs():
    """Run pre req tasks"""

    from doosra.tasks.ibm.utils_tasks import task_group_clouds_by_api_key
    task_group_clouds_by_api_key.delay()


@manager.command
def deploy():
    """Run deployment tasks."""
    from flask_migrate import upgrade

    # migrate database to latest revision
    upgrade()

    # Create pre-defined templates
    create_predefined_templates()


if __name__ == '__main__':
    manager.run()
