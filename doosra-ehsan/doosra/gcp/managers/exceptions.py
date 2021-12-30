"""
    Cloud's operations, whether fetch or push, can result in scenarios
        1. Cloud's credentials are invalid.
        2. Gateway has no credentials provided.
        3. Executing requests on a cloud was unsuccessful
    Following are the four exceptions raised on these events
"""
import json


class CloudAuthError(Exception):
    """This exception is raised if: Cloud's credentials are invalid."""

    def __init__(self, cloud_id):
        self.msg = "Invalid credentials provided for cloud"
        super(CloudAuthError, self).__init__("Invalid credentials provided for cloud {}".format(cloud_id))


class CloudInvalidRequestError(Exception):
    """ Exception raised when cloud manager is asked to perform a task which is not doable"""

    def __init__(self, message):
        self.msg = message
        super(CloudInvalidRequestError, self).__init__(self.msg)


class CloudExecuteError(Exception):
    """ Exception raised when the request runs unsuccessfully. HTTP data was invalid or unexpected"""

    def __init__(self, error):
        self.msg = None
        try:
            if not type(error) is str:
                data = json.loads(error.content.decode('utf-8'))
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                reason = data['error']['message']
                self.msg = reason
            else:
                self.msg = error
        except (ValueError, KeyError, TypeError):
            pass
        super(CloudExecuteError, self).__init__("Operation failed, Error message:\n{}".format(error))
