import logging

from doosra import db as doosradb
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers import IBMManager
from doosra.ibm.managers.exceptions import IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError
from doosra.transit_gateway.manager.tg_manager import TransitGatewayManager

LOGGER = logging.getLogger(__name__)


def list_transit_locations(ibm_cloud):
    """
    Get a list of Transit Locations where TG is available.
    :return:
    """
    try:
        ibm_manager = IBMManager(ibm_cloud, initialize_rias_ops=False, initialize_tg_manager=True)
        locations = ibm_manager.tg_manager.fetch_ops.list_transit_locations()
    except (
            IBMAuthError,
            IBMConnectError,
            IBMExecuteError,
            IBMInvalidRequestError,
    ) as ex:
        LOGGER.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return locations
