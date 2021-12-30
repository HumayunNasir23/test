import os

from config import config

AUTH_LINK = f"{os.environ.get('AUTH_LINK')}v1/users/verify"

INVALID_REQUEST = "INVALID_REQUEST: '{}'"

SCHEMA_VALIDATION_INVALID_DETAIL = """INVALID INPUT: In Schema for `{function_name}` with URL `{api_url}`, `{path}`: 
YOU PROVIDED: {path}: {value}(type={value_type})
SHOUD BE: {path}: {schema_type}({validator})
"""

# TASK Status
PENDING = "PENDING"
IN_PROGRESS = "IN_PROGRESS"
SUCCESS = "SUCCESS"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
BACKGROUND = "BACKGROUND"
COMPLETED = "COMPLETED"

# ACTIONS
# TASK Status
ADD = "ADD"
CREATE = "CREATE"
DELETE = "DELETE"
UPDATE = "UPDATE"

CREATED = "CREATED"
VALID = "VALID"

# VPC, Firewall, Instance status
CREATING = "CREATING"
UPDATING = "UPDATING"
UPDATED = "UPDATED"
DELETING = "DELETING"
DELETED = "DELETED"
ERROR_CREATING = "ERROR_CREATING"
ERROR_DELETING = "ERROR_DELETING"
ERROR_UPDATING = "ERROR_UPDATING"
CREATION_PENDING = "CREATION_PENDING"
UPDATION_PENDING = "UPDATION_PENDING"

HOST_COUNT_TO_CIDR_BLOCK_MAPPER = {
    "8": "/29",
    "16": "/28",
    "32": "/27",
    "64": "/26",
    "128": "/25",
    "256": "/24",
    "512": "/23",
    "1024": "/22",
    "2048": "/21",
    "4096": "/20",
}

# Encryption keys
flask_config = os.getenv("FLASK_CONFIG") or "default"
SALT_LENGTH = config[flask_config].SALT_LENGTH
DERIVATION_ROUNDS = config[flask_config].DERIVATION_ROUNDS
BLOCK_SIZE = config[flask_config].BLOCK_SIZE
KEY_SIZE = config[flask_config].KEY_SIZE
SECRET = config[flask_config].SECRET

# Pagination configs
MAX_PAGE_LIMIT = config[flask_config].DOOSRA_DEFAULT_PAGE_LIMIT
DEFAULT_LIMIT = config[flask_config].DOOSRA_MAX_PAGE_LIMIT

# Dictionary of Classical Image to Vpc Image
classical_vpc_image_dictionary = {
    # operatingSystem[softwareDescription[longDescription]]
    "Ubuntu 20.04-64 Minimal for VSI": ["ibm-ubuntu-20-04-3-minimal-amd64-1", "ibm-ubuntu-20-04-minimal-amd64-2",
                                        "ibm-ubuntu-20-04-2-minimal-amd64-1"],
    "Ubuntu 18.04-64 Minimal for VSI": ["ibm-ubuntu-18-04-1-minimal-amd64-1", "ibm-ubuntu-18-04-1-minimal-amd64-2",
                                        "ibm-ubuntu-18-04-5-minimal-amd64-1"],
    "Ubuntu 18.04-64 LAMP for VSI": ["ibm-ubuntu-18-04-1-minimal-amd64-1", "ibm-ubuntu-18-04-1-minimal-amd64-2",
                                     "ibm-ubuntu-18-04-5-minimal-amd64-1"],
    "Ubuntu 16.04-64 Minimal for VSI": ["ibm-ubuntu-16-04-5-minimal-amd64-1"],
    "Ubuntu 16.04-64 LAMP for VSI": ["ibm-ubuntu-16-04-5-minimal-amd64-1"],

    'CentOS 8.0-64 Minimal for VSI': ['ibm-centos-8-2-minimal-amd64-2', "ibm-centos-8-3-minimal-amd64-3"],
    'CentOS 7.0-64 Minimal for VSI': ["ibm-centos-7-6-minimal-amd64-2", "ibm-centos-7-6-minimal-amd64-1",
                                      "ibm-centos-7-9-minimal-amd64-3", "ibm-centos-7-9-minimal-amd64-4"],
    "CentOS 7.0-64 LAMP for VSI": ["ibm-centos-7-9-minimal-amd64-3", "ibm-centos-7-9-minimal-amd64-4"],

    # NO SUPPORT FROM IBM, MAPPING TO ITSELF TO MAKE MESSAGING READABLE
    "CentOS 6.0-64 Minimal for VSI": ["CentOS 6.0-64 Minimal for VSI"],
    "CentOS 6.0-64 LAMP for VSI": ["CentOS 6.0-64 LAMP for VSI"],

    "Redhat EL 8.0-64 Minimal for VSI": ["ibm-redhat-8-3-minimal-amd64-3"],
    "Redhat EL 7.0-64 Minimal for VSI": ["ibm-redhat-7-9-minimal-amd64-4", "ibm-redhat-7-9-minimal-amd64-3",
                                         "ibm-redhat-7-6-minimal-amd64-1"],
    "Redhat EL 7.0-64 LAMP for VSI": ["ibm-redhat-7-9-minimal-amd64-4", "ibm-redhat-7-9-minimal-amd64-3"],

    # NO SUPPORT FROM IBM, MAPPING TO ITSELF TO MAKE MESSAGING READABLE
    "Redhat EL 6.0-64 Minimal for VSI": ["Redhat EL 6.0-64 Minimal for VSI"],
    "Redhat EL 6.0-64 LAMP for VSI": ["Redhat EL 6.0-64 LAMP for VSI"],

    "Microsoft Windows 2019 FULL STD 64 bit 2019 FULL STD x64": ["ibm-windows-server-2019-full-standard-amd64-7",
                                                                 "ibm-windows-server-2019-full-standard-amd64-3",
                                                                 "ibm-windows-server-2019-full-standard-amd64-6"],
    "Microsoft Windows 2016 FULL STD 64 bit 2016 FULL STD x64": ["ibm-windows-server-2016-full-standard-amd64-7",
                                                                 "ibm-windows-server-2016-full-standard-amd64-3",
                                                                 "ibm-windows-server-2016-full-standard-amd64-4",
                                                                 "ibm-windows-server-2016-full-standard-amd64-6"],
    "Microsoft Windows 2012 FULL STD 64 bit 2012 FULL STD x64": ["ibm-windows-server-2012-full-standard-amd64-3",
                                                                 "ibm-windows-server-2012-full-standard-amd64-5",
                                                                 "ibm-windows-server-2012-full-standard-amd64-6"],
    "Microsoft Windows 2012 R2 FULL STD 64 bit 2012 R2 FULL STD x64": [
        "ibm-windows-server-2012-r2-full-standard-amd64-7",
        "ibm-windows-server-2012-r2-full-standard-amd64-3",
        "ibm-windows-server-2012-r2-full-standard-amd64-4",
        "ibm-windows-server-2012-r2-full-standard-amd64-6"
    ],

    "Debian 10.0.0-64 Minimal for VSI": ["ibm-debian-10-8-minimal-amd64-1", "ibm-debian-10-11-minimal-amd64-1"],
    "Debian 9.0.0-64 Minimal for VSI": ["ibm-debian-9-12-minimal-amd64-1", "ibm-debian-9-12-minimal-amd64-2",
                                        "ibm-debian-9-13-minimal-amd64-2", "ibm-debian-9-13-minimal-amd64-4"],
    "Debian 9.0.0-64 LAMP for VSI": ["ibm-debian-9-13-minimal-amd64-4"],

    # NO SUPPORT FROM IBM, MAPPING TO ITSELF TO MAKE MESSAGING READABLE
    "Debian 8.0.0-64 Minimal for VSI": ["Debian 8.0.0-64 Minimal for VSI"],
    "Debian 8.0.0-64 LAMP for VSI": ["Debian 8.0.0-64 LAMP for VSI"],
    "Debian 7.0.0-64 Minimal for VSI": ["Debian 7.0.0-64 Minimal for VSI"],
}

PRIVATE_KEY_NAME = "{}-{}"

# qcow2 format string
QCOW2 = "qcow2"
COS_FILE_EXTENSIONS = {"vhd", "qcow2"}
