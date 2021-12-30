from doosra.migration.data_migration.linux import Linux


class CentOS(Linux):
    def __init__(self):
        super().__init__()
        self.CHECK_IF_PACKAGE_INSTALLED = "rpm -qa | grep {package}"
        self.PACKAGE_MANAGER = "yum"
        self.PACKAGES = ["wget", "curl", "bc", "jq"]
        self.qemu_package = "qemu-img"
        self.EXPORT_NON_INTERACTIVE = False
        self.UPDATE = False
        self.qemu_custom_installation = False
