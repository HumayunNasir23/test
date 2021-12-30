class GenerateSshKeyException(Exception):
    """Exception generating ssh key"""

    def __init__(self):
        super(GenerateSshKeyException, self).__init__("SSH key not generated.. try again to register vpc account")
