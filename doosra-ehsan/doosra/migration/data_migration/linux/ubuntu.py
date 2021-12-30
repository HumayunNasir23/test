from doosra.migration.data_migration.linux import Linux


class Ubuntu(Linux):
    def __init__(self):
        super().__init__()
        self.CHECK_IF_PACKAGE_INSTALLED = "dpkg -s {package}"
        self.PACKAGE_MANAGER = "apt"
        self.PACKAGES = ["wget", "curl", "bc", "jq"]
        self.qemu_package = "qemu-utils"
        self.EXPORT_NON_INTERACTIVE = True
        self.UPDATE = True
        self.qemu_custom_installation = False
