"""
This file contains exceptions raised by ICSoftlayerManager
"""


class SLAuthException(Exception):
    """
    Raised when softlayer credentials for image conversion account are wrong
    """
    def __init__(self):
        self.msg = "WHO MESSED WITH SOFTLAYER CREDENTIALS FOR IMAGE MIGRATION ACCOUNT?!"
        super(SLAuthException, self).__init__(self.msg)


class SLResourceNotFoundException(Exception):
    """
    Raised when an operation is performed for an object that does not exit in cloud
    """
    def __init__(self, message):
        self.msg = message
        super(SLResourceNotFoundException, self).__init__(self.msg)


class UnexpectedSLError(Exception):
    """
    The only exceptions expected are wrapped in this file but due to bad documentation of IBM code, we can not foresee
    what exceptions can be raised by their client. This is to handle such errors that occur in their APIs (only)
    """
    def __init__(self, ex):
        self.msg = "Fault Code: {}\nReason:{}".format(ex.faultCode, ex.reason)
        super(UnexpectedSLError, self).__init__(self.msg)
