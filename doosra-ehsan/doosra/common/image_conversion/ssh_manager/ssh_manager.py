"""
This file contains the code for SSHManager class which hosts the SSH Client functionality
"""
import socket
from io import StringIO

import paramiko
from paramiko.ssh_exception import AuthenticationException, BadAuthenticationType, BadHostKeyException, \
    NoValidConnectionsError, SSHException

from .exceptions import SFTPFileUploadFailure, SFTPFileWriteFailure, SSHAuthException, SSHCommandException, \
    SSHConnectException, SSHNoCredentialsException


class SSHManager:
    """
    Manager for SSH Operations.
    Can send file using SFTP
    Can run single commands and returns its exit code and outputs(stdout and stderr)

    Please remember to close the client ( <ssh_manager_object_name>.close_ssh_connection() ) after using this class.
    """
    TIMEOUT = 8.0

    def __init__(self, hostname, username="root", password=None, port="22", private_key=None, pass_phrase=None):
        """
        Constructor for class SSHManager
        :param hostname: <string> IP or DNS name of host
        :param username: <string> user of host (default: root)
        :param password: <string> password of the host (only used if SSH key is not provided)
        :param port: <string> ssh port for remote host (default: 22)
        :param private_key: <string> ssh private key as string (Password is ignored if SSH Key is provided)
        :param pass_phrase: <string> pass phrase to decode private key (Optional-Not required if private key not provided or
               private key is not encrypted)
        :raises SSHAuthException: If authentication is failed (passed through __connect function)
        :raises SSHConnectException: if unable to connect to host (passed through __connect function)
        :raises SSHNoCredentialsException: If no credentials are provided to connect to remote host
        """
        if not ((username and password) or (username and private_key)):
            raise SSHNoCredentialsException(hostname)

        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.private_key = None
        self.pass_phrase = None
        if private_key:
            self.private_key = paramiko.RSAKey.from_private_key(StringIO(private_key))
            self.pass_phrase = pass_phrase

        self.__ssh_client = paramiko.SSHClient()
        self.__ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.__connect()

    def __connect(self):
        """
        Private function to connect ssh client to remote host if the connection does not already exist
        :raises SSHAuthException: If authentication is failed
        :raises SSHConnectException: if unable to connect to host
        """
        if self.__ssh_client and self.__ssh_client.get_transport():
            return

        client_args = dict(hostname=self.hostname, username=self.username)
        client_args["port"] = int(self.port)
        client_args['look_for_keys'] = False
        client_args['timeout'] = self.TIMEOUT
        if self.private_key:
            client_args['pkey'] = self.private_key
            if self.pass_phrase:
                client_args['passphrase'] = self.pass_phrase
        else:
            client_args['password'] = self.password

        try:
            print("Starting SSH session to: '{}'".format(self.hostname))
            self.__ssh_client.connect(**client_args)
        except (AuthenticationException, BadAuthenticationType, BadHostKeyException) as ex:
            print("An exception of type {0} was raised. Arguments:\n{1!r}".format(type(ex).__name__, ex.args))
            raise SSHAuthException(self.hostname, self.username)
        except (SSHException, NoValidConnectionsError, socket.timeout, socket.error) as ex:
            print("An exception of type {0} was raised. Arguments:\n{1!r}".format(type(ex).__name__, ex.args))
            raise SSHConnectException(self.hostname)

    def send_file_sftp(self, local_file_path, remote_file_path=None):
        """
        Send a file to host using SFTP as the transfer protocol. Rewrites if a file with same name exists with the same
        path.
        :param local_file_path: <string> complete path of the file to send (including filename and extension)
        :param remote_file_path: <string> (optional) complete path of where to the file for remote host (including
        filename and extension)

        :raises SFTPFileUploadFailure in case file upload fails
        """
        # TODO: checks on whether remote file path exists or not can be enhanced. Not doing that due to time constraint.
        # TODO: No exceptions stated in paramiko docs so they will pass through. We can catch those with testing.
        self.__connect()

        if not remote_file_path:
            local_file_name = local_file_path.split("/")[-1]
            remote_file_path = "./" + local_file_name

        sftp_client = self.__ssh_client.open_sftp()
        try:
            sftp_client.put(local_file_path, remote_file_path)
        except (IOError, FileNotFoundError) as ex:
            sftp_client.close()
            raise SFTPFileUploadFailure(self.hostname, local_file_path, remote_file_path, ex)

        sftp_client.close()

    def run_command(self, command):
        """
        Run a single command on the remote host
        :param command: <string> command to run on the remote host

        :raises SSHCommandException In case SSH Manager is unable to run the command on remote server (this is not to
                be confused with an invalid command as that would result in an erroneous exit code and output)

        :return: <tuple> 2-tuple containing exit code and concatenated output and error stream.
        """
        self.__connect()

        try:
            in_stream, out_stream, error_stream = self.__ssh_client.exec_command(command)
        except SSHException as ex:
            raise SSHCommandException(self.hostname, command, ex)
        else:
            output = ""
            for stream in [out_stream, error_stream]:
                for line in stream:
                    output += line

            exit_code = out_stream.channel.recv_exit_status()
            out_stream.channel.close()

            if exit_code:
                raise SSHCommandException(self.hostname, command, "Exit Code: {}\nOUTPUT: {}".format(
                    str(exit_code), output))
            return output

    def write_file(self, file_dir, file_name, file_contents):
        """
        Write a file on the remote host
        :param file_dir: <string> directory path (will be created if does not exist) e.g /root/some_folder
        :param file_name: <string> file name with extension e.g some_file.txt
        :param file_contents: <string> content to write to the file

        :raises SFTPFileWriteFailure: in case the file can not be written due to any issues such as permissions etc
        """
        self.__connect()

        if file_dir[-1] == "/":
            file_dir = file_dir[:-1]
        sftp_client = self.__ssh_client.open_sftp()
        try:
            sftp_client.chdir(file_dir)
        except IOError:
            try:
                sftp_client.mkdir(file_dir)
            except IOError:
                sftp_client.close()
                raise SFTPFileWriteFailure(file_dir, file_name, self.hostname, "Could not create directory")
            try:
                sftp_client.chdir(file_dir)
            except IOError:
                sftp_client.close()
                raise SFTPFileWriteFailure(file_dir, file_name, self.hostname, "Could not switch to directory")

        try:
            with sftp_client.open(file_dir + "/" + file_name, 'w') as remote_file:
                remote_file.write(file_contents)
        except IOError:
            raise SFTPFileWriteFailure(file_dir, file_name, self.hostname, "Could not open file")
        finally:
            sftp_client.close()

    def close_ssh_connection(self):
        """
        This function closes the transport for client. This SHOULD ALWAYS be called after using ssh manager object.
        """
        if self.__ssh_client:
            self.__ssh_client.close()

    def __del__(self):
        """
        This destructor is just for safety in case someone forgets to close the client. However, it should be done
        explicitly
        """
        self.close_ssh_connection()
