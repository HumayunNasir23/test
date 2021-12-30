class WorkflowTerminated(Exception):
    """Raise when any exception occur against a workflow"""

    def __init__(self, msg):
        super(Exception, self).__init__("WORKFLOW TERMINATED for {}".format(msg))


class TaskFailureError(Exception):
    """Raise when any exception occur against a workflow"""

    def __init__(self, msg):
        super(Exception, self).__init__("Task Failure Error {}".format(msg))
