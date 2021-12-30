from operator import itemgetter

from flask import current_app, jsonify, Response

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.models import ProjectReleaseNotes
from doosra.users import users


@users.route('/users/release_notes', methods=['GET'])
@authenticate
def get_release_notes(user_id, user):
    """" Get all release notes """
    project_release_notes = doosradb.session.query(ProjectReleaseNotes).filter_by(project_id=user.project.id).all()

    if not project_release_notes:
        current_app.logger.info("No Release notes found against {id}".format(id=user.project.id))
        return Response(status=204)

    release_notes_list = list()
    for project_release_note in project_release_notes:
        release_notes_list.append(project_release_note.release_notes.to_json())

    sorted_release_notes_list = sorted(release_notes_list, key=itemgetter('release_date'), reverse=True)
    return jsonify(sorted_release_notes_list)
