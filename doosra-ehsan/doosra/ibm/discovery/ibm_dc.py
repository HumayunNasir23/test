from flask import current_app

from doosra import db as doosradb
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMCloud


class IBMDiscoveryClient(object):
    def __init__(self, cloud):
        assert isinstance(cloud, IBMCloud), "Invalid parameter 'cloud': Only 'IBMCloud' type object allowed"
        self.cloud = cloud
        self.ibm_manager = IBMManager(self.cloud)

    def run_discovery(self):
        try:
            regions = self.ibm_manager.rias_ops.fetch_ops.get_regions()
            for region in regions:
                self.ibm_manager = IBMManager(self.cloud, region)
                self.sync_floating_ips(region)
                self.sync_ssh_keys(region)
                self.sync_vpcs(region)
                self.sync_ike_policies(region)
                self.sync_ipsec_policies(region)
                self.sync_custom_images(region)

        except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
            current_app.logger.info(ex)
            if isinstance(ex, IBMAuthError):
                self.cloud.status = INVALID
            doosradb.session.commit()
        else:
            return True

    def sync_vpcs(self, region):
        """
        Discover Network VPCs within a region on IBM Cloud
        :return:
        """
        vpc_list = list()
        current_app.logger.info(
            "Starting discovery of VPC Networks for IBM Cloud with ID '{id}' in region '{region}'".format(
                id=self.cloud.id, region=region))

        ibm_manager = IBMManager(self.cloud, region)
        vpc_list.extend(
            ibm_manager.rias_ops.fetch_ops.get_all_vpcs(fetch_instances=True, fetch_lbs=True, fetch_vpns=True))

        for vpc in self.cloud.vpc_networks.filter_by(region=region).all():
            found = False
            for vpc_ in vpc_list:
                if vpc.name == vpc_.name:
                    found = True
                    break

            if not found:
                doosradb.session.delete(vpc)
                doosradb.session.commit()

        for vpc in vpc_list:
            vpc.add_update_db()

    def sync_floating_ips(self, region):
        """
        Discover Floating IPs within a region on IBM Cloud
        :return:
        """
        floating_ips_list = list()
        current_app.logger.info(
            "Starting discovery of Floating IPs for IBM Cloud with ID '{id}' in region '{region}'".format(
                id=self.cloud.id, region=region))

        ibm_manager = IBMManager(self.cloud, region)
        floating_ips_list.extend(ibm_manager.rias_ops.fetch_ops.get_all_floating_ips())

        for floating_ip in self.cloud.floating_ips.filter_by(region=region).all():
            found = False
            for floating_ip_ in floating_ips_list:
                if floating_ip.name == floating_ip_.name:
                    found = True
                    break

            if not found:
                doosradb.session.delete(floating_ip)
                doosradb.session.commit()

        for floating_ip in floating_ips_list:
            floating_ip.add_update_db()

    def sync_ssh_keys(self, region):
        """
        Discover SSH Keys within a region on IBM Cloud
        :return:
        """
        ssh_keys_list = list()
        current_app.logger.info(
            "Starting discovery of SSH Keys for IBM Cloud with ID '{id}' in region '{region}'".format(
                id=self.cloud.id, region=region))
        ibm_manager = IBMManager(self.cloud, region)
        ssh_keys_list.extend(ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys())

        for ssh_key in self.cloud.ssh_keys.filter_by(region=region).all():
            found = False
            for ssh_key_ in ssh_keys_list:
                if ssh_key.name == ssh_key_.name:
                    found = True
                    break
            if not found:
                doosradb.session.delete(ssh_key)
                doosradb.session.commit()

        for ssh_key in ssh_keys_list:
            ssh_key.add_update_db()

    def sync_ike_policies(self, region):
        """
        Discover IKE Policies within a region on IBM Cloud
        :return:
        """
        ike_policies_list = list()
        current_app.logger.info(
            "Starting discovery of IKE Policies for IBM Cloud with ID '{id}' in region '{region}'".format(
                id=self.cloud.id, region=region))
        ibm_manager = IBMManager(self.cloud, region)
        ike_policies_list.extend(ibm_manager.rias_ops.fetch_ops.get_all_ike_policies())

        for ike_policy in self.cloud.ike_policies.filter_by(region=region).all():
            found = False
            for ike_policy_ in ike_policies_list:
                if ike_policy.name == ike_policy_.name:
                    found = True
                    break
            if not found:
                doosradb.session.delete(ike_policy)
                doosradb.session.commit()

        for ike_policy in ike_policies_list:
            ike_policy.add_update_db()

    def sync_ipsec_policies(self, region):
        """
        Discover IKE Policies within a region on IBM Cloud
        :return:
        """
        ipsec_policies_list = list()
        current_app.logger.info(
            "Starting discovery of IPsec Policies for IBM Cloud with ID '{id}' in region '{region}'".format(
                id=self.cloud.id, region=region))
        ibm_manager = IBMManager(self.cloud, region)
        ipsec_policies_list.extend(ibm_manager.rias_ops.fetch_ops.get_all_ipsec_policies())

        for ipsec_policy in self.cloud.ipsec_policies.filter_by(region=region).all():
            found = False
            for ipsec_policy_ in ipsec_policies_list:
                if ipsec_policy.name == ipsec_policy_.name:
                    found = True
                    break

            if not found:
                doosradb.session.delete(ipsec_policy)
                doosradb.session.commit()

        for ipsec_policy in ipsec_policies_list:
            ipsec_policy.add_update_db()

    def sync_custom_images(self, region):
        """
        Discover custom images within a region on IBM Cloud
        :return:
        """
        images_list = list()
        current_app.logger.info(
            "Starting discovery of images for IBM Cloud with ID '{id}' in region '{region}'".format(
                id=self.cloud.id, region=region))
        ibm_manager = IBMManager(self.cloud, region)
        images_list.extend(ibm_manager.rias_ops.fetch_ops.get_all_images())

        for image in self.cloud.images.filter_by(region=region).all():
            found = False
            for image in images_list:
                if image.name == image.name:
                    found = True
                    break

            if not found:
                doosradb.session.delete(image)
                doosradb.session.commit()

        for image in images_list:
            image.add_update_db()
