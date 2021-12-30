RESOURCE_MANAGER_SERVICE_NAME = "cloudresourcemanager"
COMPUTE_ENGINE_SERVICE_NAME = "compute"

# Google Response Status
DONE = "DONE"

# The value at zero-th index contains project_id for the image family to get latest images from Google.
DEFAULT_IMAGES_PROJECTS = (("centos-cloud", "centos-6", "centos-7", "centos-8"),
                           ("cos-cloud", "cos-81-lts", "cos-77-lts", "cos-73-lts", "cos-69-lts", "cos-beta", "cos-dev",
                            "cos-stable"),
                           ("coreos-cloud", "coreos-alpha", "coreos-beta", "coreos-stable"),
                           ("debian-cloud", "debian-9", "debian-10"),
                           ("rhel-cloud", "rhel-6", "rhel-7", "rhel-8"),
                           ("rhel-sap-cloud", "rhel-7-7-sap-ha", "rhel-7-6-sap-ha", "rhel-7-4-sap"),
                           ("suse-cloud", "sles-15", "sles-12"),
                           ("suse-sap-cloud",
                            "sles-15-sp1-sap", "sles-15-sap", "sles-12-sp5-sap", "sles-12-sp4-sap",
                            "sles-12-sp3-sap", "sles-12-sp2-sap"),
                           ("ubuntu-os-cloud",
                            "ubuntu-minimal-2004-lts", "ubuntu-2004-lts",
                            "ubuntu-minimal-1910", "ubuntu-1910",
                            "ubuntu-minimal-1804-lts", "ubuntu-1804-lts",
                            "ubuntu-1604-lts", "ubuntu-minimal-1604-lts",),
                           ("windows-sql-cloud",
                            "sql-ent-2019-win-2019", "sql-std-2019-win-2019", "sql-web-2019-win-2019",
                            "sql-ent-2017-win-2016", "sql-exp-2017-win-2016", "sql-std-2017-win-2016",
                            "sql-web-2017-win-2016", "sql-exp-2017-win-2012-r2", "sql-ent-2016-win-2016",
                            "sql-std-2016-win-2016", "sql-ent-2016-win-2012-r2", "sql-std-2016-win-2012-r2",
                            "sql-web-2016-win-2012-r2", "sql-ent-2014-win-2016", "sql-ent-2014-win-2012-r2",
                            "sql-std-2014-win-2012-r2", "sql-web-2014-win-2012-r2", "sql-ent-2012-win-2012-r2",
                            "sql-std-2012-win-2012-r2", "sql-web-2012-win-2012-r2"),
                           ("windows-cloud",
                            "windows-1909-core", "windows-1909-core-for-containers", "windows-1903-core",
                            "windows-1903-core-for-containers",
                            "windows-1809-core-for-containers", "windows-1809-core",
                            "windows-2012-r2-core", "windows-2012-r2", "windows-2016-core", "windows-2016",
                            "windows-2019-core-for-containers", "windows-2019-core",
                            "windows-2019-for-containers", "windows-2019"))
