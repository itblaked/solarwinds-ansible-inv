#!/usr/bin/env python


'''
Custom dynamic inventory script for Ansible and Solar Winds, in Python.
This was tested on Python 2.7.6, Orion 2016.2.100, and Ansible  2.3.0.0.

(c) 2017, Chris Babcock (chris@bluegreenit.com)

https://github.com/cbabs/solarwinds-ansible-inv

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

NOTE:  This software is free to use for any reason or purpose. That said, the
author request that improvements be submitted back to the repo or forked
to something public.

'''
import argparse
import ConfigParser
import requests
import re
import os

try:
    import json
except ImportError:
    import simplejson as json

from urllib3 import disable_warnings, exceptions as urllib3exc
disable_warnings(category=urllib3exc.InsecureRequestWarning)

config_file = os.environ.get('NPM_INI_FILE') or 'solarwinds.ini'

#Get configuration variables
config = ConfigParser.ConfigParser()
config.readfp(open(config_file))

# Orion Server IP or DNS/hostname
server = os.environ.get('NPM_SERVER') or config.get('solarwinds', 'npm_server')

# Orion Username
user = os.environ.get('NPM_USER') or config.get('solarwinds', 'npm_user')

# Orion Password
password = os.environ.get('NPM_PASS') or config.get('solarwinds', 'npm_password')

# Field for groups
groupField = os.environ.get('NPM_GROUPFIELD') or 'GroupName'

# Field for host
hostField = os.environ.get('NPM_HOSTFIELD') or 'SysName'

# Below is the default payload option.
payload = os.environ.get('NPM_PAYLOAD') or "query=SELECT C.Name as GroupName, N.SysName FROM Orion.Nodes as N JOIN Orion.ContainerMemberSnapshots as CM on N.NodeID = CM.EntityID JOIN Orion.Container as C on CM.ContainerID=C.ContainerID WHERE CM.EntityDisplayName = 'Node' AND N.Vendor = 'Cisco'"

use_groups = os.environ.get('NPM_USE_GROUPS') or 'True'
parentField = os.environ.get('NPM_PARENTFIELD') or 'ParentGroupName'
childField = os.environ.get('NPM_CHILDFIELD') or 'ChildGroupName'

group_payload = os.environ.get('NPM_GROUP_PAYLOAD') or "query=SELECT C.Name as ParentGroupName, CM.Name as ChildGroupName FROM Orion.ContainerMemberSnapshots as CM JOIN Orion.Container as C on CM.ContainerID=C.ContainerID WHERE CM.EntityDisplayName = 'Group'"

url = "https://"+server+":17778/SolarWinds/InformationService/v3/Json/Query"


class SwInventory(object):

    # CLI arguments
    def read_cli(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--host')
        parser.add_argument('--list', action='store_true')
        self.options = parser.parse_args()

    def __init__(self):
        # Initialize  inventory
        self.inventory = {'_meta': {'hostvars': {}}}
        self.read_cli_args()

        # Called with `--list`.
        if self.args.list:
            self.inventory, self.query_data = self.get_hosts(self.inventory, payload)
            self.inventory = self.write_hosts_to_inventory(self.inventory, self.query_data)
            self.inventory = self.set_category_groups(self.inventory)
            self.inventory = self.add_groups_to_categories(self.inventory, self.query_data)
            self.inventory = self.add_hosts_to_primary_group(self.inventory, self.query_data)
            self.inventory = self.add_hosts_to_secondary_group(self.inventory, self.query_data)
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.empty_inventory()
        # If args return empty inventory.
        else:
            self.inventory = self.empty_inventory()

        # Print inventory for Ansible to consume
        print(json.dumps(self.inventory, indent=2))
        
    def get_hosts(self, inventory, payload):
        req = requests.get(url, params=payload, verify=False, auth=(user, password))
        hostsData = req.json()
        query_data = eval(json.dumps(hostsData))
        return inventory, query_data

    def write_hosts_to_inventory(self, inventory, query_data):
        # Add hosts and variables to inventory
        for host in query_data['results']:
            inventory['_meta']['hostvars'].update({host[hostField]: { 
                "ansible_host": host[hostField], 
                "AppOwner": host['AppOwner'], 
                "MachineType": host['MachineType'], 
                "Environment": host['Environment'],
                "Asset_Group": host['Asset_Group'],
                "Responsible_Teams": host['Responsible_Teams'],
                "NodeID": host['NodeID']
            }})
        return inventory

    def add_hosts_to_primary_group(self, inventory, query_data):
        # Add hosts to primary group
        for host in query_data['results']:
            if host[parentField] in inventory:
                if host[hostField] not in inventory[host[parentField]]['hosts']:
                    inventory[host[parentField]]['hosts'].append(host[hostField])
            else:
                inventory[host[parentField]] = {'hosts': [host[hostField]]}
                inventory[host[parentField]].update({'children': []})
        return inventory

    def add_hosts_to_secondary_group(self, inventory, query_data):
        for host in query_data['results']:
            if host[childField] in inventory:
                if host[hostField] not in inventory[host[childField]]['hosts']:
                    inventory[host[childField]]['hosts'].append(host[hostField])
            else:
                inventory[host[childField]] = {'hosts': [host[hostField]]}
                inventory[host[childField]].update({'children': []})
        return inventory

    def set_category_groups(self, inventory):
        inventory.update({
            "all": {
                "children": [
                    "Windows",
                    "Linux",
                    "Network",
                    "Other"
                ],
                "hosts": [],
                "vars": {},
            },
            "Linux": {
                "children": [],
                "hosts": [],
                "vars": {},
            },
            "Windows": {
                "children": [],
                "hosts": [],
                "vars": {},
            },
            "Network": {
                "children": [],
                "hosts": [],
                "vars": {},
            },
            "Other": {
                "children": [],
                "hosts": [],
                "vars": {},
            },
        })
        return inventory

    def add_groups_to_categories(self, inventory, query_data):
        for host in query_data['results']:
            if "Windows" in host[childField]:
                if host[childField] not in inventory['Windows']['children']:
                        inventory['Windows']['children'].append(host[childField])
            elif ("Linux" in host[childField]) or ("Red Hat" in host[childField]) or ("Debian" in host[childField]):
                if host[childField] not in inventory['Linux']['children']:
                        inventory['Linux']['children'].append(host[childField])
            elif ("Cisco" in host[childField]) or ("Catalyst" in host[childField]):
                if host[childField] not in inventory['Network']['children']:
                        inventory['Network']['children'].append(host[childField])
            else:
                if host[childField] not in inventory['Other']['children']:
                        inventory['Other']['children'].append(host[childField])
        return inventory

    @staticmethod
    def clean_inventory_item(item):
        # item = re.sub('[^A-Za-z0-9]+', '_', item)
        return item

    # Empty inventory for testing.
    def empty_inventory(self):
        return {'_meta': {'hostvars': {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action='store_true')
        parser.add_argument('--host', action='store')
        self.args = parser.parse_args()

# Get the inventory.
SwInventory()