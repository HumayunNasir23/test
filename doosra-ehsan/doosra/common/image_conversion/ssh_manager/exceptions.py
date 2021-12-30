"""
This file contains all of the exceptions raised by SSH Manager
"""


class SSHAuthException(Exception):
    """
    Raised when client can not authenticate SSH connection with the remote host
    """
    def __init__(self, hostname, username):
        super(SSHAuthException, self).__init__(
            "Invalid SSH credentials provided\nHostname: {hostname}\nUsername: {username}".format(
                hostname=hostname, username=username))


class SSHConnectException(Exception):
    """
    Raised when client is unable to connect to the remote host
    """
    def __init__(self, hostname):
        super(SSHConnectException, self).__init__("Device {} inaccessible".format(hostname))


class SSHCommandException(Exception):
    """
    Raised when client is unable to run a command on remote server (this is not to be confused with an invalid command
    as that would result in an erroneous exit code and output)
    """
    def __init__(self, hostname, commands, error):
        self.msg = "Running the following commands on device {} failed:\nCommands: {}\nMessage: {}".format(
            hostname, commands, error)
        super(SSHCommandException, self).__init__(self.msg)

    def __str__(self):
        return self.msg


class SSHNoCredentialsException(Exception):
    """
    Raised when no or not enough credentials are provided to the SSH Manager
    """
    def __init__(self, hostname):
        self.msg = "No credentials provided for host: {}".format(hostname)
        super(SSHNoCredentialsException, self).__init__(self.msg)

    def __str__(self):
        return self.msg


class SFTPFileUploadFailure(Exception):
    """
    Raised when client fails to upload a file on the remote host
    """
    def __init__(self, hostname, local_file_path, remote_file_path, error):
        self.msg = "Unable to upload file using SFTP on host {}.\nLocal File: {}\nRemote File: {}\nError: {}".format(
            hostname, local_file_path, remote_file_path, error)
        super(SFTPFileUploadFailure, self).__init__(self.msg)

    def __str__(self):
        return self.msg


class SFTPFileWriteFailure(Exception):
    """
    Raised when client fails to write a file on the remote host
    """
    def __init__(self, file_dir, file_name, hostname, error):
        self.msg = "Unable to write file '{}' in directory '{}' on host '{}'.\nError: {}".format(
            file_name, file_dir, hostname, error)
        super(SFTPFileWriteFailure, self).__init__(self.msg)

    def __str__(self):
        return self.msg
