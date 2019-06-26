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
        self.inventory = {}
        self.read_cli_args()

        # Called with `--list`.
        if self.args.list:
            self.inventory = self.get_list()
            print("host dict" + json.dumps(self.inventory, indent=2))

            if use_groups:
                self.groups = self.get_groups(self.inventory)
                #self.add_groups_to_hosts(self.groups, self.inventory)
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.empty_inventory()
        # If no groups or vars are present, return empty inventory.
        else:
            self.inventory = self.empty_inventory()

        print(json.dumps(self.inventory, indent=2))
        
    def get_list(self):
        req = requests.get(url, params=payload, verify=False, auth=(user, password))
        hostsData = req.json()
        dumped = eval(json.dumps(hostsData))
        print("hosts payload" + json.dumps(dumped, indent=2))

        # Inject data below to speed up script
        final_dict = {'_meta': {'hostvars': {}}}

        # Add host variables to dictionary
        for m in dumped['results']:
            final_dict['_meta']['hostvars'].update({m[hostField]: { 
                "ansible_host": m[hostField], 
                "AppOwner": m['AppOwner'], 
                "MachineType": m['MachineType'], 
                "Environment": m['Environment'],
                "Asset_Group": m['Asset_Group'],
                "Responsible_Teams": m['Responsible_Teams'],
                "NodeID": m['NodeID']
                }})

        # Add hosts to primary group
        for host in dumped['results']:
            if host[parentField] in final_dict:
                if host[hostField] not in final_dict[host[parentField]]['hosts']:
                    final_dict[host[parentField]]['hosts'].append(host[hostField])
            else:
                final_dict[host[parentField]] = {'hosts': [host[hostField]]}
                final_dict[host[parentField]].update({'children': []})
        return final_dict

    def get_groups(self, inventory):
        req = requests.get(url, params=group_payload, verify=False, auth=(user, password))
        hostsData = req.json()
        dumped = eval(json.dumps(hostsData))

        print("group payload" + json.dumps(dumped, indent=2))
        
        inventory.update({
            "all": {
                "children": [
                    "Windows",
                    "Linux",
                    "Network"
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
        })
        for m in dumped['results']:
            # Allow Upper/lower letters and numbers. Replace everything else with underscore
            #m[parentField] = self.clean_inventory_item(m[parentField])
            #m[childField] = self.clean_inventory_item(m[childField])

            if m[parentField] not in inventory['all']['children']:
                    inventory['all']['children'].append(m[parentField])

            if "Windows" in m[childField]:
                if m[childField] not in inventory['Windows']['children']:
                        inventory['Windows']['children'].append(m[childField])

            if ("Linux" in m[childField]) or ("Red Hat" in m[childField]) or ("Debian" in m[childField]):
                if m[childField] not in inventory['Linux']['children']:
                        inventory['Linux']['children'].append(m[childField])

            if ("Cisco" in m[childField]) or ("Catalyst" in m[childField]):
                if m[childField] not in inventory['Network']['children']:
                        inventory['Network']['children'].append(m[childField])

            if m[parentField] in inventory:
                if m[childField] not in inventory[m[parentField]]['children']:
                    inventory[m[parentField]]['children'].append(m[childField])
            else:
                inventory[m[parentField]] = {'children': [m[childField]]}
        return inventory

    def add_groups_to_hosts (self, groups, inventory):
        inventory.update(groups)
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
