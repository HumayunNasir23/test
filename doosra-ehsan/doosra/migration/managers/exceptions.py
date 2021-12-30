class SLAuthError(Exception):
    """This exception is raised if: Cloud's credentials are invalid."""

    def __init__(self, username):
        self.msg = "Invalid credentials provided for SoftLayer Account"
        super(SLAuthError, self).__init__("Invalid credentials provided for SoftLayer Account {}".format(username))


class SLInvalidRequestError(Exception):
    """ Exception raised when cloud manager is asked to perform a task which is not doable"""

    def __init__(self, message):
        self.msg = message
        super(SLInvalidRequestError, self).__init__(message)


class SLExecuteError(Exception):
    """ Exception raised when the request runs unsuccessfully. HTTP data was invalid or unexpected"""

    def __init__(self, error):
        self.msg = error.reason
        self.error_code = error.faultCode
        super(SLExecuteError, self).__init__(
            "Operation failed, FaultCode: {}, Reason:\n{}".format(self.error_code, self.msg))


class SLRateLimitExceededError(Exception):
    """ Exception raised when the request runs unsuccessfully. HTTP data was invalid or unexpected"""

    def __init__(self, error):
        self.msg = error.reason
        super(SLRateLimitExceededError, self).__init__(
            "Rate Limit Exceeded for Request:\n{}".format(self.msg))
