#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
 
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError
 
import yaml
import configparser
from ipaddress import IPv4Network

 
# --- GLOBALS ---
config = configparser.ConfigParser()
routes = {}


# load config file
def load_config(_file):
    global config
    config = configparser.ConfigParser(delimiters='=')
    config.optionxform=str
    config.read(_file)

 
# open the given file as a yml. if fails returns False
def open_yaml_file(_file):
    with open(_file) as file_yaml:
        try:
            return yaml.load(file_yaml, Loader=yaml.FullLoader)
        except yaml.YAMLError as err:
            raise AnsibleError(err)

 
# checks the format of the yml file
def validate_yaml_file(_file):
    global routes
    routes = open_yaml_file(_file)


# generate route command
def generate_route(state, network, gateway):
    command = config['GENERAL']['CMD']
    return command.format(state=state, network=network, gateway=gateway)
    

# get related interface
def get_interface(source):
    interface = config['PDC'][source].split(':')[0]
    return interface


# gets related gateway
def get_gateway(source):
    gateway = config['PDC'][source].split(':')[1]
    return gateway


# gets related core interface's ip
def get_core_ip(source):
    core = config['PDC'][source].split(':')[2]
    return core


# converts ip address to network format
def set_network(destination):
    dest = IPv4Network(destination)
    return dest


# process input and generate route configs
def processor(state):
    global routes, config

    tmp_route_config = {}
    tmp_route_status = {}

    for route in routes['temporary_routes']:
        core_ip = get_core_ip(route['source'])
        tmp_routes = []
        tmp_status = []

        for dest in route['destinations']:
            network = set_network(dest)
            gateway = get_gateway(route['source'])
            cmd = generate_route(state, str(network), gateway)
            tmp_routes.append(cmd)
            tmp_status.append(str(network[0]))


        if core_ip in tmp_route_config.keys():
            tmp_route_config[core_ip] = list(set( tmp_route_config[core_ip] + tmp_routes ))
            tmp_route_status[core_ip] = tmp_route_status[core_ip] + '|'.join(tmp_status)
        else:
            tmp_route_config[core_ip] = tmp_routes
            tmp_route_status[core_ip] = '|'.join(tmp_status)
      
    return tmp_route_config, tmp_route_status


# main function of Ansible module
def main():
    module_args = dict(
        route_path=dict(type='str', required=True),
        config_path=dict(type='str', required=True),
        state=dict(type='str', required=True)
    )
 
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
 
    try:
        validate_yaml_file(module.params['route_path'])
        load_config(module.params['config_path'])
        routes, status = processor(module.params['state'])

        result = dict(route_config=routes, route_status=status, rc=0)
        module.exit_json(**result)

    except Exception as err:
        result = dict(msg=str(err), rc=1)
        module.fail_json(**result)
 
 
if __name__ == '__main__':
    main()


