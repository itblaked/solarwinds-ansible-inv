
from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = '''
    name: solarwinds
    plugin_type: inventory
    author:
      - Blake Douglas (@itblaked)
    short_description: Ansible dynamic inventory plugin for Solarwinds.
    version_added: "2.9"
    description:
        - Reads inventories from SolarWinds.
        - Supports reading configuration from both YAML config file and environment variables.
        - If reading from the YAML file, the file name must end with solarwinds.(yml|yaml) or solarwinds_inventory.(yml|yaml),
          the path in the command would be /path/to/solarwinds_inventory.(yml|yaml). If some arguments in the config file
          are missing, this plugin will try to fill in missing arguments by reading from environment variables.
        - If reading configurations from environment variables, the path in the command must be @solarwinds_inventory.
    options:
        plugin:
            description: the name of this plugin, it should always be set to 'solarwinds'
                for this plugin to recognize it as it's own.
            env:
                - name: ANSIBLE_INVENTORY_ENABLED
            required: True
            choices: ['solarwinds']
        host:
            description: The network address and port of your Solarwinds host.
            type: string
            env:
                - name: SOLARWINDS_HOST
            required: True
        username:
            description: The user that you plan to use to access inventories on Solarwinds.
            type: string
            env:
                - name: SOLARWINDS_USERNAME
            required: True
        password:
            description: The password for your Solarwinds user.
            type: string
            env:
                - name: SOLARWINDS_PASSWORD
            required: True
        hostname_field:
            description: SolarWinds field to use as Ansible hostname.
            type: string
            env:
                - name: SOLARWINDS_HOSTNAME_FIELD
            required: True
            default: DNS
        category_field: 
            description: 
                - SolarWinds field which should be used to group hosts by.
                - E.g. category_field: MachineType
            type: string
            env:
                - name: SOLARWINDS_CATEGORY_FIELD
            required: False
            default: "MachineType"
        hostvar_fields:
            description
                - List of fields to map to host variables.
                - These should match columns defined in the SolarWinds query.
                - Specified as a comma-separated string, it will be converted into a list.
                - E.g. hostvar_fields: "DNS,IP,Asset_group"
            type: string
            env:
                - name: SOLARWINDS_HOSTVAR_FIELDS
            required: False
            default: "DNS,IP,Asset_group"
        group_on_fields:
            description:
                - List of fields to create groups of hosts from.
                - If empty string or False, no additional groups will be created other than OS groups.
                - These should match columns defined in the SolarWinds query.
                - Specified as a comma-separated string, it will be converted into a list.
                - E.g. group_on_fields: "Asset_group,MachineType"
            type: string
            env:
                - name: SOLARWINDS_GROUP_ON_FIELDS
            required: False
            default: "Asset_group,MachineType"
        categories_definition:
            description: 
                - SolarWinds categories.
                - E.g. "Windows;Linux:Linux,Red Hat,Debian;Network:Cisco,Catalyst;Other:"
            type: string
            env:
                - name: SOLARWINDS_CATEGORIES    
            default: "Windows;Linux:Linux,Red Hat,Debian;Network:Cisco,Catalyst;Other:"
            required: False
        query:
            description: 
                - SolarWinds query in 'SWSQL' format to send to SolarWinds via REST API
                - E.g. "SELECT CP.Asset_Group, SysName, DNS, IP, MachineType FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID"
            type: string
            env:
                - name: SOLARWINDS_QUERY
            default: "SELECT CP.Asset_Group, SysName, DNS, IP, MachineType FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID"
            required: False
        validate_certs:
            description: Specify whether Ansible should verify the SSL certificate of Solarwinds host.
            type: bool
            default: True
            env:
                - name: SOLARWINDS_VERIFY_SSL
            required: False
            aliases: [ verify_ssl ]
'''

EXAMPLES = '''
# Before you execute the following commands, you should make sure this file is in your plugin path,
# and you enabled this plugin.

# Example for using solarwinds_inventory.yml file

plugin: solarwinds
host: your_solarwinds_server_network_address
username: your_solarwinds_username
password: your_solarwinds_password
hostname_field: DNS
category_field: MachineType
hostvar_fields: DNS,IP,Asset_group
group_on_fields: Asset_group,MachineType
categories_definition: "Windows;Linux:Linux,Red Hat,Debian;Network:Cisco,Catalyst;Other:"
query: "SELECT CP.Asset_Group, SysName, DNS, IP, MachineType FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID"
validate_certs: True

# Then you can run the following command.
# If some of the arguments are missing, Ansible will attempt to read them from environment variables.
# ansible-inventory -i /path/to/solarwinds_inventory.yml --list

# Example for reading from environment variables:

# Set environment variables:
# export SOLARWINDS_HOST=YOUR_SOLARWINDS_HOST_ADDRESS
# export SOLARWINDS_USERNAME=YOUR_SOLARWINDS_USERNAME
# export SOLARWINDS_PASSWORD=YOUR_SOLARWINDS_PASSWORD
# Read the inventory specified in SOLARWINDS_INVENTORY from Solarwinds, and list them.
# The inventory path must always be @solarwinds_inventory if you are reading all settings from environment variables.
# ansible-inventory -i @solarwinds_inventory --list
'''

import re
import os
import json
from ansible.module_utils import six
from ansible.module_utils.urls import Request, urllib_error, ConnectionError, socket, httplib
from ansible.module_utils._text import to_text, to_native
from ansible.errors import AnsibleParserError, AnsibleOptionsError
from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.config.manager import ensure_type

# Python 2/3 Compatibility
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


class InventoryModule(BaseInventoryPlugin):
    NAME = 'solarwinds'
    # Stays backward compatible with solarwinds inventory script.
    # If the user supplies '@solarwinds_inventory' as path, the plugin will read from environment variables.
    no_config_file_supplied = False

    def make_request(self, request_handler, solarwinds_url, query_url, query):
        """Makes the request to given URL, handles errors, returns JSON
        """
        try:
            response = request_handler.get(query_url, params="query="+query)
        except (ConnectionError, urllib_error.URLError, socket.error, httplib.HTTPException) as e:
            n_error_msg = 'Connection to remote host failed: {err}'.format(err=to_native(e))
            # If Solarwinds gives a readable error message, display that message to the user.
            if callable(getattr(e, 'read', None)):
                n_error_msg += ' with message: {err_msg}'.format(err_msg=to_native(e.read()))
            raise AnsibleParserError(n_error_msg)

        # Attempt to parse JSON.
        try:
            return json.loads(response.read())
        except (ValueError, TypeError) as e:
            # If the JSON parse fails, print the ValueError
            raise AnsibleParserError('Failed to parse json from host: {err}'.format(err=to_native(e)))

    def verify_file(self, path):
        if path.endswith('@solarwinds_inventory'):
            self.no_config_file_supplied = True
            return True
        elif super(InventoryModule, self).verify_file(path):
            return path.endswith(('solarwinds_inventory.yml', 'solarwinds_inventory.yaml', 'solarwinds.yml', 'solarwinds.yaml'))
        else:
            return False

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        if not self.no_config_file_supplied and os.path.isfile(path):
            self._read_config_data(path)
        # Read inventory from solarwinds server.
        # Note the environment variables will be handled automatically by InventoryManager.
        solarwinds_host = self.get_option('host')
        if not re.match('(?:http|https)://', solarwinds_host):
            solarwinds_host = 'https://{solarwinds_host}'.format(solarwinds_host=solarwinds_host)

        request_handler = Request(url_username=self.get_option('username'),
                                  url_password=self.get_option('password'),
                                  force_basic_auth=True,
                                  validate_certs=self.get_option('validate_certs'))

        query_url = "/SolarWinds/InformationService/v3/Json/Query"
        solarwinds_url = urljoin(solarwinds_host, query_url)
        inventory = {'_meta': {'hostvars': {}}}
        inventory = self.make_request(request_handler, solarwinds_url)

        # Clean up the inventory.
        self.inventory.reconcile_inventory()