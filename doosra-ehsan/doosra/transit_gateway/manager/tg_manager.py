from doosra.ibm.managers.operations.iam.iam_operations import IAMOperations
from doosra.ibm.managers.operations.resource.resource_operations import ResourceOperations
from doosra.models import IBMCloud
from doosra.transit_gateway.manager.operations.fetch_operations import FetchOperations
from doosra.transit_gateway.manager.operations.push_operations import PushOperations


class TransitGatewayManager(object):
    """
    TransitGatewayManager Should be the entry for all the Operations related to TransitGateway
    For FetchOperations, use the initialize_fetch_ops
    For PushOperations, use the initialize_push_ops
    """

    def __init__(self, cloud, resource_ops, initialize_fetch_ops=False, initialize_push_ops=False):

        assert isinstance(cloud, IBMCloud), "Invalid parameter 'cloud': Only 'IBMCloud' type object allowed"

        self.iam_ops = IAMOperations(cloud)
        self.resource_ops = resource_ops

        if initialize_fetch_ops:
            self.fetch_ops = FetchOperations(cloud, self.iam_ops)

        if initialize_push_ops:
            self.push_ops = PushOperations(cloud, self.iam_ops, self.resource_ops)
