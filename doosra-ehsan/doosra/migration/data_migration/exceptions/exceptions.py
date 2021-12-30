class PackageInstallationException(Exception):
    def __init__(self, package):
        super(PackageInstallationException, self).__init__(
            "Package not installed\nPackage: {package}".format(package=package)
        )


class VolumeAttachmentException(Exception):
    def __init__(self, host):
        super(VolumeAttachmentException, self).__init__(
            "Volume attachment Exception(No Volume attached)\nMachine: {host}\n".format(
                host=host
            )
        )


class DataMigrationFailedException(Exception):
    def __init__(self, host, status):
        super(DataMigrationFailedException, self).__init__(
            "Data Migration Failed.. !\nMachine: {host} with status: {status}".format(
                host=host, status=status
            )
        )


class ImageCorruptException(Exception):
    def __init__(self, image, dire):
        super(ImageCorruptException, self).__init__(
            "Image is corrupted or partially downloaded or some issue with directory !"
            "\nImage: {image}, directory: {dir}".format(image=image, dir=dire)
        )


class OperatingSystemNameException(Exception):
    def __init__(self, os_name):
        super(OperatingSystemNameException, self).__init__(
            "{os_name} does not belong Linux(Ubuntu, CentOS, RedHat, Debian)".format(
                os_name=os_name
            )
        )
