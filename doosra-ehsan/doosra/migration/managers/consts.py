NETWORK_VLAN_MASK = (
    "[virtualGuests[datacenter.longName, "
    "operatingSystem[softwareLicense[softwareDescription[manufacturer, version]]], "
    "fullyQualifiedDomainName, maxCpu, maxMemory, networkComponents[name, maxSpeed, speed, port, primaryIpAddress, "
    "securityGroupBindings[securityGroup[rules[remoteGroup[description]]]]], "
    "regionalGroup[name], sshKeys[fingerprint, key, label], firewallServiceComponent[rules, status]], vlanNumber]"
)

LOAD_BALANCER_MASK = (
    "mask[healthMonitors, l7Pools, listeners[defaultPool[healthMonitor, members, sessionAffinity]], "
    "members, sslCiphers, datacenter]"
)

SUBNET_MASK = "[subnets]"

VIRTUAL_SERVER_MASK = (
    "mask[datacenter.longName, id, dedicatedHost[id], status, type, scaleMember, allowedNetworkStorage[storageType], "
    "operatingSystem[softwareLicense[softwareDescription[name, manufacturer, version, longDescription]]], "
    "fullyQualifiedDomainName, hostname, dedicatedAccountHostOnlyFlag, maxCpu, maxCpuUnits, maxMemory, "
    "networkComponents[name, networkVlan, primarySubnet, maxSpeed, speed, port, primaryIpAddress, "
    "securityGroupBindings[securityGroup[rules[remoteGroup[description]]]]], "
    "regionalGroup[name], sshKeys[fingerprint, key, label], firewallServiceComponent[rules, status],"
    "blockDevices[diskImage]]"
)

VSI_ID_HOSTNAME_ONLY_MASK = "mask[id, hostname]"
DEDICATED_HOST_WO_INSTANCES_MASK = "mask[cpuCount, diskCapacity, id, memoryCapacity, name, datacenter, guests[id]]"
DEDICATED_HOST_W_INSTANCES_MASK = "mask[cpuCount, diskCapacity, id, memoryCapacity, name, datacenter, guests]"

IMAGE_MASK = "mask[id,name,children[blockDevices[diskImage[softwareReferences[softwareDescription[longDescription]]]]]]"
