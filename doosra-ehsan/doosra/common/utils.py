import base64
import copy
import hashlib
import random

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from flask import current_app
from ipcalc import Network
from random import randrange

from doosra.common.consts import *


def calculate_address_range(from_address, to_address):
    """
    Calculate Address Range for addresses extracted from Vyatta Gateway
    :return:
    """
    address_list = list()
    try:
        address_prefix = ".".join(from_address.split("-")[0].split(".")[:-2])
        from_address_split = from_address.split(".")
        to_address_split = to_address.split(".")

        from_address_3rd_octet = int(from_address_split[2])
        from_address_4th_octet = int(from_address_split[3])
        to_address_3rd_octet = int(to_address_split[2])
        to_address_4th_octet = int(to_address_split[3])

        for octet_3 in range(from_address_3rd_octet, to_address_3rd_octet + 1):
            if octet_3 not in [from_address_3rd_octet, to_address_3rd_octet]:
                for octet_4 in range(0, 256):
                    address_list.append(
                        address_prefix + "." + str(octet_3) + "." + str(octet_4)
                    )
            elif octet_3 == from_address_3rd_octet and octet_3 == to_address_3rd_octet:
                for octet_4 in range(from_address_4th_octet, to_address_4th_octet + 1):
                    address_list.append(
                        address_prefix + "." + str(octet_3) + "." + str(octet_4)
                    )
            elif octet_3 == from_address_3rd_octet:
                for octet_4 in range(from_address_4th_octet, 256):
                    address_list.append(
                        address_prefix + "." + str(octet_3) + "." + str(octet_4)
                    )
            elif octet_3 == to_address_3rd_octet:
                for octet_4 in range(0, to_address_4th_octet + 1):
                    address_list.append(
                        address_prefix + "." + str(octet_3) + "." + str(octet_4)
                    )
    except ValueError as e:
        return

    return address_list


def get_network(ip_range):
    """
    Get network from provided IP
    :param ip_range:
    :return:
    """
    try:
        ip = Network(ip_range)
        network = "{}/{}".format(str(ip.network()), str(ip.subnet()))
    except ValueError as e:
        current_app.logger.debug(e)
        return
    return network


def get_obj_type(obj):
    """
    This method return obj type for class objects
    :return:
    """
    if not obj:
        return

    return obj.__class__.__name__


def get_cidr_block_size(address_count):
    """
    This method return the cidr block size provided the address count.
    returns /24 for 256
    :return:
    """
    return HOST_COUNT_TO_CIDR_BLOCK_MAPPER[address_count]


def get_subnet_cidr_block(address_prefix, host_count):
    """
    This method exctracts the required host addresses from the address prefix, returns the
    updated host prefix and ip range
    :return:
    """
    try:
        address_prefix = Network(address_prefix)
        cidr_block_size = get_cidr_block_size(host_count)
        split_address = str(address_prefix).split("/")
        if not len(split_address) == 2:
            return

        ip_range = split_address[0] + cidr_block_size
        address_prefix = address_prefix.__add__(int(host_count))

    except ValueError as e:
        current_app.logger.debug(e)
        return

    return ip_range, address_prefix


def is_overlapping_range(ip_range, subnetworks):
    """
    This method checks for IP range collision
    :return:
    """
    if not subnetworks:
        return

    try:
        ip_range = Network(ip_range)
        for subnet in subnetworks:
            subnet = Network(subnet)
            if ip_range.check_collision(subnet):
                return True

    except ValueError as e:
        current_app.logger.debug(e)
        return


def validate_subnets(subnets):
    """
    Validate subnets list, There cannot be duplicate subnets in the list.
    :param subnets:
    :return:
    """
    ip_range = [subnet["ip_range"] for subnet in subnets]
    if len(ip_range) != len(set(ip_range)):
        return False

    for ip in ip_range:
        if not validate_ip_range(ip):
            return False

    return True


def validate_ip_range(ip_range):
    """
    Validate Ip range
    :return:
    """
    try:
        ips = Network(ip_range)
    except ValueError as e:
        current_app.logger.debug(e)
        return
    return True


def validate_ip_in_range(subnet_ip, address_prefix):
    try:
        ips = Network(address_prefix)
        if subnet_ip in ips:
            return True
    except ValueError as e:
        current_app.logger.debug(e)
        return


def is_private_ip(ip):
    try:
        network = Network(ip)
        if network.info() == "PRIVATE":
            return ip
    except ValueError as e:
        return


def is_private(ip):
    try:
        network = Network(ip)
        if network.info() == "PRIVATE":
            return True
        return False
    except ValueError as e:
        return


def get_image_name(manufacturer, version, architecture="amd64"):
    return "{manufacturer}-{version}-{architecture}".format(
        manufacturer=manufacturer, version=version, architecture=architecture
    )


def encrypt_api_key(api_key):
    """Encrypt api_key"""

    try:
        salt = get_random_bytes(SALT_LENGTH)
        iv = get_random_bytes(BLOCK_SIZE)

        derived_secret = hashlib.pbkdf2_hmac(
            hash_name='sha256', password=SECRET.encode(), salt=salt, iterations=DERIVATION_ROUNDS)
        length = 16 - (len(api_key) % 16)
        api_key += chr(length) * length
        cipher = AES.new(derived_secret, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(api_key) + iv + salt)
    except Exception as e:
        current_app.logger.info(
            "Exception raised while encrypting: {0} Exception message: {1}".format(
                api_key, e
            )
        )
        return api_key


def decrypt_api_key(api_key):
    """Decrypt api_key"""

    try:
        secret_key = base64.b64decode(api_key)
        start_iv = len(secret_key) - BLOCK_SIZE - SALT_LENGTH
        start_salt = len(secret_key) - SALT_LENGTH
        data, iv, salt = (
            secret_key[:start_iv],
            secret_key[start_iv:start_salt],
            secret_key[start_salt:],
        )
        derived_secret = hashlib.pbkdf2_hmac(hash_name="sha256", password=SECRET.encode(), salt=salt,
                                             iterations=DERIVATION_ROUNDS)

        derived_secret = derived_secret[:KEY_SIZE]
        cipher = AES.new(derived_secret, AES.MODE_CBC, iv)
        secret_key = cipher.decrypt(data)
        length = secret_key[-1]
        return secret_key[:-length].decode("utf-8")
    except Exception as e:
        current_app.logger.info(
            "Exception raised while decrypting: {0} Exception message: {1}".format(
                api_key, e
            )
        )
        return api_key


def get_image_key(dictionary, value_image):
    for k, v in dictionary.items():
        if value_image in v:
            return k
    return None


def transform_ibm_name(name):
    """
    This method transform a given string into IBM allowed string names. It does so by
    1) Check for special characters
    2) Check for names starting with Numbers
    3) Checks for more than one consecutive hyphens within a given string
    4) Check for first character to be an upper case character or number and then transforms accordingly.
    :return:
    """
    try:
        ibm_name = name.lower().translate({ord(name_string): "-" for name_string in " !@#$%^&*()[]{};:,./<>?\|`~-=_+"})
        while "--" in ibm_name:
            ibm_name = ibm_name.replace("--", "-")

        if ibm_name and ibm_name[0].isdigit():
            ibm_name = f"ibm-{ibm_name}"

        return ibm_name

    except Exception as ex:
        current_app.logger.debug(ex)
        return name


def return_cos_object_name(ibm_manger, bucket_name, object_name):
    """concatenate an integer value if this object already exist in this bucket"""
    object_actual_name = copy.copy(object_name)
    cos_objects = ibm_manger.cos_ops.fetch_ops.get_bucket_objects(bucket_name=bucket_name)
    for i in [random.randint(1, 1000) for i in range(50)]:
        for obj in cos_objects:
            if object_name in obj:
                object_name = object_actual_name + str(i)
                break

        return object_name


def return_vpc_image_name(ibm_manager, image_name, region, visibility="private"):
    """concatenate an integer value if this image already exist in this region"""
    actual_img_name = copy.copy(image_name)
    custom_images_list = ibm_manager.rias_ops.fetch_ops.get_all_images(name=image_name, visibility=visibility)
    for i in [random.randint(1, 1000) for i in range(50)]:
        for img in custom_images_list:
            if img.region == region:
                image_name = actual_img_name + str(i)
                break

        return image_name


def remove_duplicates(seq: list) -> list:
    """
    Remove all the duplicates from a list with Preserving order.
    With using set on list, the order is not preserved while duplicates are removed.
    :param seq: A list
    :return:
    """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def get_volume_attachment_dict(capacity, zone, name, index_, region=None, iops=3000):
    """
    Get ibm volume attachments and ibm volume const dictionaries
    """
    volume_name = f"{name}{randrange(100)}{index_}"[-62:]

    volume_attachment = {'name': volume_name, 'type': 'data', 'is_delete': True, "capacity": int(capacity),
                         'volume': {'name': volume_name, 'capacity': capacity, "is_migration_enabled": False,
                                    'iops': iops, 'zone': zone, 'encryption': 'provider_managed',
                                    'profile': {'name': 'general-purpose', 'family': 'tiered',
                                                'region': region or zone[:-2]},
                                    'status': 'CREATED', 'original_capacity': capacity}
                         }
    return volume_attachment
