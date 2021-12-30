import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey, PrimaryKeyConstraint, JSON
from sqlalchemy.orm import relationship, backref

from doosra import db
from doosra.common.consts import PENDING

classic_kubernetes_zone_subnets = db.Table(
    "classic_kubernetes_zone_subnets",
    Column(
        "zone_id",
        String(32),
        ForeignKey("kubernetes_cluster_worker_pool_zones.id"),
        nullable=False,
    ),
    Column("subnets_id", String(32), ForeignKey("ibm_subnets.id"), nullable=False),
    PrimaryKeyConstraint("zone_id", "subnets_id"),
)


class KubernetesCluster(db.Model):
    __tablename__ = "kubernetes_clusters"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    pod_subnet = Column(String(255), nullable=True)
    service_subnet = Column(String(255), nullable=True)
    kube_version = Column(String(255), nullable=False)
    disable_public_service_endpoint = Column(Boolean, nullable=False)
    state = Column(String(255))
    status = Column(String(255))
    provider = Column(String(50), nullable=False)
    cluster_type = Column(String(32))
    resource_id = Column(String(64))
    is_workspace = Column(Boolean, nullable=False, default=False)
    workloads = Column(JSON)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))
    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    worker_pools = relationship(
        "KubernetesClusterWorkerPool",
        backref="kubernetes_clusters",
        cascade="all, delete-orphan",
        lazy="dynamic")

    def __init__(self, name, kube_version, disable_public_service_endpoint, provider, cluster_type=None,
                 resource_id=None, pod_subnet=None, service_subnet=None, state=None, status=None, vpc_id=None,
                 cloud_id=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.pod_subnet = pod_subnet
        self.service_subnet = service_subnet
        self.kube_version = kube_version
        self.disable_public_service_endpoint = disable_public_service_endpoint
        self.state = state
        self.status = status
        self.provider = provider
        self.cluster_type = cluster_type
        self.resource_id = resource_id
        self.vpc_id = vpc_id
        self.cloud_id = cloud_id

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "pod_subnet": self.pod_subnet,
            "service_subnet": self.service_subnet,
            "kube_version": self.kube_version,
            "disable_public_service_endpoint": self.disable_public_service_endpoint,
            "state": self.state,
            "status": self.status,
            "provider": self.provider,
            "type": self.cluster_type,
            "resource_id": self.resource_id,
            "is_workspace": self.is_workspace,
            "cloud_id": self.cloud_id,
            "workloads": self.workloads,
            "vpc_id": self.vpc_id,
            "vpc": self.ibm_vpc_network.name if self.ibm_vpc_network else None,
            "worker_pools": [worker_pool.to_json() for worker_pool in self.worker_pools.all()]
        }

    def make_copy(self):
        obj = KubernetesCluster(
            name=self.name,
            pod_subnet=self.pod_subnet,
            service_subnet=self.service_subnet,
            kube_version=self.kube_version,
            disable_public_service_endpoint=self.disable_public_service_endpoint,
            state=self.state,
            status=self.status,
            provider=self.provider,
            cluster_type=self.cluster_type,
            vpc_id=self.vpc_id,
            cloud_id=self.cloud_id
        )
        for worker_pool in self.worker_pools.all():
            obj.worker_pools.append(worker_pool.make_copy())

        if self.ibm_resource_group:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()

        if self.is_workspace:
            obj.is_workspace = self.is_workspace

        return obj

    def get_existing_from_db(self, vpc=None):
        if vpc:
            return db.session.query(self.__class__).filter_by(
                name=self.name, cloud_id=self.cloud_id, vpc_id=vpc.id).first()

        return db.session.query(self.__class__).filter_by(
            name=self.name, cloud_id=self.cloud_id, vpc_id=self.vpc_id).first()

    def add_update_db(self, vpc=None):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            worker_pools = self.worker_pools.all()
            self.worker_pools = list()
            ibm_resource_group = self.ibm_resource_group
            self.ibm_resource_group = None
            if ibm_resource_group:
                ibm_resource_group = ibm_resource_group.add_update_db()
            self.ibm_vpc_network = vpc
            self.ibm_resource_group = ibm_resource_group
            db.session.add(self)
            db.session.commit()
            for worker_pool in worker_pools:
                worker_pool.add_update_db(self)

            return self

    def to_json_body(self, managed_view=None):
        return {
            "disablePublicServiceEndpoint": self.disable_public_service_endpoint,
            "kubeVersion": self.kube_version,
            "name": self.name,
            "podSubnet": self.pod_subnet,
            "provider": self.provider,
            "type": self.cluster_type,
            "serviceSubnet": self.service_subnet,
            "workerPool": [workerpool.to_json_body() for workerpool in self.worker_pools.all()][0] if managed_view else
            self.worker_pools.first().to_json_body()
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        status = None
        cluster = KubernetesCluster(
            name=json_body["name"],
            disable_public_service_endpoint=True,
            kube_version=json_body["masterKubeVersion"],
            provider=json_body["provider"],
            resource_id=json_body["id"],
            pod_subnet=json_body['podSubnet'],
            service_subnet=json_body['serviceSubnet'],
            state=json_body['state'],
            status=status,
            cluster_type=json_body['type']
        )

        return cluster

    def to_report_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": PENDING,
            "message": ""
        }


class KubernetesClusterWorkerPool(db.Model):

    __tablename__ = "kubernetes_cluster_worker_pools"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    disk_encryption = Column(Boolean, nullable=False, default=True)
    flavor = Column(String(255), nullable=False)
    worker_count = Column(String(32), nullable=False)
    resource_id = Column(String(64))
    kubernetes_cluster_id = Column(String(32), ForeignKey('kubernetes_clusters.id'), nullable=False)
    zones = relationship(
        "KubernetesClusterWorkerPoolZone",
        backref="kubernetes_cluster_worker_pools",
        cascade="all, delete-orphan",
        lazy="dynamic")

    def __init__(self, name, disk_encryption, flavor, worker_count):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.disk_encryption = disk_encryption
        self.flavor = flavor
        self.worker_count = worker_count

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "disk_encryption": self.disk_encryption,
            "flavor": self.flavor,
            "worker_count": self.worker_count,
            "zones": [zone.to_json() for zone in self.zones.all()]
        }

    def make_copy(self):
        obj = KubernetesClusterWorkerPool(
            name=self.name,
            disk_encryption=self.disk_encryption,
            flavor=self.flavor,
            worker_count=self.worker_count,
            )
        for zone in self.zones.all():
            obj.zones.append(zone.make_copy())

        return obj

    def get_existing_from_db(self, k8s_cluster):
        if k8s_cluster:
            return db.session.query(self.__class__).filter_by(
                name=self.name, kubernetes_cluster_id=k8s_cluster.id).first()

        return db.session.query(self.__class__).filter_by(
            name=self.name, kubernetes_cluster_id=self.kubernetes_cluster_id).first()

    def add_update_db(self, k8s_cluster):
        existing = self.get_existing_from_db(k8s_cluster)
        if not existing:
            zones = self.zones.all()
            self.zones = list()
            self.kubernetes_clusters = k8s_cluster
            db.session.add(self)
            db.session.commit()
            for zone in zones:
                zone.add_update_db(self, k8s_cluster)
                db.session.commit()

            return self

    def to_json_body(self):
        return {
            "diskEncryption": self.disk_encryption,
            "flavor": self.flavor,
            "name": self.name,
            "workerCount": int(self.worker_count),
            "zones": [zone.to_json_body() for zone in self.zones.all()]

        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        k8s_worker_pool = KubernetesClusterWorkerPool(
            name=json_body['name'],
            disk_encryption=True,
            flavor=json_body['machineType'],
            worker_count=json_body['sizePerZone']
        )

        return k8s_worker_pool


class KubernetesClusterWorkerPoolZone(db.Model):

    __tablename__ = "kubernetes_cluster_worker_pool_zones"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    private_vlan = Column(String(255))
    worker_pool_id = Column(String(32), ForeignKey('kubernetes_cluster_worker_pools.id'))
    subnets = relationship(
        "IBMSubnet",
        secondary=classic_kubernetes_zone_subnets,
        backref=backref("kubernetes_cluster_worker_pool_zones"),
        lazy="dynamic",
    )

    def __init__(self, name, private_vlan=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.private_vlan = private_vlan

    def to_json(self):
        return {
            "id": self.id,
            "zone": self.name,
            "subnets": [subnet.name for subnet in self.subnets.all()]
        }

    def make_copy(self):
        obj = KubernetesClusterWorkerPoolZone(
            self.name)
        for subnet in self.subnets.all():
            obj.subnets.append(subnet.make_copy())

        return obj

    def get_existing_from_db(self, worker_pool=None):
        if worker_pool:
            return db.session.query(self.__class__).filter_by(
                name=self.name, worker_pool_id=worker_pool.id).first()

        return db.session.query(self.__class__).filter_by(
            name=self.name, worker_pool_id=self.worker_pool_id).first()

    def add_update_db(self, worker_pool, k8s_cluster):
        existing = self.get_existing_from_db(worker_pool)
        if not existing:
            subnets = self.subnets.all()
            self.subnets = list()
            self.kubernetes_cluster_worker_pools = worker_pool
            db.session.add(self)
            db.session.commit()

            for subnet in subnets:
                self.subnets.append(subnet.add_update_db(k8s_cluster.ibm_vpc_network))

            return self

    def to_json_body(self):

        return {
            "id": self.name,
            "subnetID": [subnet.resource_id for subnet in self.subnets.all() if subnet.zone == self.name][0]
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        k8s_worker_pool_zone = KubernetesClusterWorkerPoolZone(
            name="dummy-zone",
            private_vlan=json_body["privateVlan"]
        )
        return k8s_worker_pool_zone

    @classmethod
    def from_ibm_json_body_zone(cls, json_body):
        ibm_k8s_worker_pool_zone = KubernetesClusterWorkerPoolZone(
            name=json_body["id"]
        )
        return ibm_k8s_worker_pool_zone
