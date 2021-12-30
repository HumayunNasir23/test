from doosra.ibm.managers.operations.cos.cos_operations import COSOperations
from doosra.ibm.managers.operations.iam.iam_operations import IAMOperations
from doosra.ibm.managers.operations.resource.resource_operations import ResourceOperations
from doosra.ibm.managers.operations.rias.rias_operations import RIASOperations
from doosra.models import IBMCloud
from doosra.transit_gateway.manager.tg_manager import TransitGatewayManager


class IBMManager(object):
    """
    IBM Manager should be the entry point for all IBM related operations
    """

    def __init__(self, cloud, region=None, initialize_rias_ops=True, initialize_tg_manager=False):
        """
        Initialize IBM Manager object
        :param cloud: An object of class IBMCloud
        """
        assert isinstance(cloud, IBMCloud), "Invalid parameter 'cloud': Only 'IBMCloud' type object allowed"

        self.iam_ops = IAMOperations(cloud)
        self.resource_ops = ResourceOperations(cloud, self.iam_ops)
        if initialize_rias_ops:
            self.rias_ops = RIASOperations(cloud, region, self.iam_ops, self.resource_ops)

        if initialize_tg_manager:
            self.tg_manager = TransitGatewayManager(cloud, self.resource_ops, initialize_fetch_ops=True,
                                                    initialize_push_ops=True)

        if cloud.service_credentials:
            self.cos_ops = COSOperations(cloud, region, cloud.service_credentials.resource_instance_id)
