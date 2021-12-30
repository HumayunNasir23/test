import json
from os import listdir
from os.path import isfile, join

from doosra.vpc_templates.consts import IBM_TEMPLATES_PATH


def load_json_templates():
    """
    Load template files from json files
    :return:
    """
    template_files_list, templates_list = list(), list()
    for file in listdir(IBM_TEMPLATES_PATH):
        if not (isfile(join(IBM_TEMPLATES_PATH, file)) and file.lower().endswith('.json')):
            continue

        template_files_list.append(''.join([IBM_TEMPLATES_PATH, file]))

    for template_file in template_files_list:
        with open(template_file) as json_file:
            templates_list.append(json.load(json_file))

    return templates_list
