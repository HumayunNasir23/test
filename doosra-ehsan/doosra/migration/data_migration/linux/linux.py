import logging
from doosra.migration.data_migration.consts import QEMU_CUSTOM_INSTALLATION
from doosra.migration.data_migration.operating_system import BaseOS

LOGGER = logging.getLogger("doosra/operating_system.py")


class Linux(BaseOS):
    INSTALL_PACKAGE_COMM = "{package_manager} -y install {package_name}"
    UPDATE_COMM = "{package_manager} update"
    EXPORT_NON_INTERACTIVE_COMM = "export DEBIAN_FRONTEND=noninteractive"

    def __init__(self):
        self.CHECK_IF_PACKAGE_INSTALLED = ""
        self.PACKAGE_MANAGER = None
        self.PACKAGES = []
        self.installed_package = []
        self.qemu_package = None
        self.UPDATE = False
        self.EXPORT_NON_INTERACTIVE = False
        self.qemu_custom_installation = False

    @property
    def bash_installation_string(self):
        packages = " ".join(self.PACKAGES)
        if not self.qemu_custom_installation:
            packages += " {}".format(self.qemu_package)

        com_string = self.INSTALL_PACKAGE_COMM.format(package_manager=self.PACKAGE_MANAGER, package_name=packages)

        if self.UPDATE:
            update_string = self.UPDATE_COMM.format(package_manager=self.PACKAGE_MANAGER)
            com_string = """{update_string} \n{com_string}""".format(update_string=update_string, com_string=com_string)

        if self.EXPORT_NON_INTERACTIVE:
            com_string = "{export_variable} \n{com_string}".format(export_variable=self.EXPORT_NON_INTERACTIVE_COMM, com_string=com_string)

        if self.qemu_custom_installation:
            com_string = "{com_string} \n {qemu_custom_installation}".format(com_string=com_string,qemu_custom_installation=QEMU_CUSTOM_INSTALLATION)

        return com_string
