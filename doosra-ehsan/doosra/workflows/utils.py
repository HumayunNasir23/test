import logging

from doosra import models
from doosra.models import WorkflowRoot, WorkflowTask

LOGGER = logging.getLogger(__name__)


def get_resource_json(workflow_root):
    """
    Generates JSON of a successfully completed CREATION WorkflowRoot's main resource
    :param workflow_root: <Object: WorkflowRoot> The workflow root from which to extract main resource's info
    :return:
    """
    resource_json = {}
    try:
        if workflow_root.status != WorkflowRoot.STATUS_C_SUCCESSFULLY or workflow_root.workflow_nature != "CREATE":
            LOGGER.info(
                f"Can not get resource json for status '{workflow_root.status}', "
                f"nature '{workflow_root.workflow_nature}'"
            )
            return resource_json

        resource_type = workflow_root.workflow_name.split()[0]
        if not resource_type:
            LOGGER.info(f"No resource type found for workflow root {workflow_root.id}")
            return resource_json

        if resource_type not in models.__all__:
            LOGGER.info(f"Resource type {resource_type} not found in models")
            return resource_json

        creation_task = workflow_root.associated_tasks.filter(
            WorkflowTask.task_type == WorkflowTask.TYPE_CREATE, WorkflowTask.resource_type == resource_type,
            WorkflowTask.resource_id != None
        ).first()
        if not creation_task:
            LOGGER.info(workflow_root.to_json())
            LOGGER.info(f"Could not find creation task for {resource_type} in parent data")
            return resource_json

        db_model = getattr(models, resource_type)

        resource = db_model.query.filter_by(id=creation_task.resource_id).first()
        if not resource:
            LOGGER.info(f"{resource_type} with id {creation_task[WorkflowTask.RESOURCE_ID_KEY]} not found in db")
            return resource_json

        resource_json = resource.to_json()
    except Exception as ex:
        LOGGER.info(str(ex))
    finally:
        return resource_json
