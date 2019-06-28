#!/usr/bin/env python

'''
Custom dynamic inventory script for Ansible and Solar Winds, in Python.
This was tested on:
Orion v3
ansible-2.7.10-1.el7ae.noarch
ansible-tower-server-3.4.3-1.el7.x86_64
Python 2.7.5 (default, Mar 26 2019, 22:13:06)
[GCC 4.8.5 20150623 (Red Hat 4.8.5-36)] on linux2

(c) 2019 Vinny Valdez <vvaldez@redhat.com> and David Castellani <dcastell@redhat.com>

Based on original work by Chris Babcock (chris@bluegreenit.com)
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

# Field for hostname
hostname_field = os.environ.get('NPM_HOSTNAME_FIELD') or 'DNS'

# Field that contains Operating System
os_field = os.environ.get('NPM_OS_FIELD') or 'MachineType'

# List of fields to map to host variables 
# these should match columns defined in the payload query. 
# Specified as a comma-separated string, will be converted into an array
hostvar_fields = os.environ.get('NPM_HOSTVAR_FIELDS') or "DNS,IP,Asset_Group"
hostvar_fields = hostvar_fields.split(',')

# List of fields to to create and add hosts to
group_on_fields = os.environ.get('NPM_GROUP_ON_FIELDS') or 'Asset_Group,MachineType'
group_on_fields = group_on_fields.split(',')

# SWSQL query to send to SolarWinds via REST API
payload = os.environ.get('NPM_PAYLOAD') or "query=SELECT CP.Asset_Group as Asset_Group, SysName, DNS, IP, MachineType FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID"

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
            self.query_results = self.get_hosts(payload)
            self.inventory = self.write_hosts_to_inventory(self.inventory, self.query_results)
            self.inventory = self.create_os_groups(self.inventory)
            self.inventory = self.add_subgroups_to_os_groups(self.inventory, self.query_results)
            for group in group_on_fields:
                self.inventory = self.add_hosts_to_group(self.inventory, self.query_results, group)
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.empty_inventory()
        # If args return empty inventory.
        else:
            self.inventory = self.empty_inventory()

        # Print inventory for Ansible to consume
        print(json.dumps(self.inventory, indent=2))
        
    def get_hosts(self, payload):
        req = requests.get(url, params=payload, verify=False, auth=(user, password))
        query_results = req.json()
        return query_results

    def write_hosts_to_inventory(self, inventory, query_results):
        # Add hosts and variables to inventory
        for host in query_results['results']:
            inventory['_meta']['hostvars'].update({host[hostname_field]: {"ansible_host": host[hostname_field] }})
            for field in hostvar_fields:
                inventory['_meta']['hostvars'][host[hostname_field]][field] = max(host[field],'')
        return inventory

    def add_hosts_to_group(self, inventory, query_results, group):
        for host in query_results['results']:
            if host[group] in inventory:
                if host[hostname_field] not in inventory[host[group]]['hosts']:
                    inventory[host[group]]['hosts'].append(host[hostname_field])
            else:
                inventory[host[group]] = {'hosts': [host[hostname_field]]}
                inventory[host[group]].update({'children': []})
        return inventory

    def create_os_groups(self, inventory):
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

    def add_subgroups_to_os_groups(self, inventory, query_results):
        for host in query_results['results']:
            if "Windows" in host[os_field]:
                if host[os_field] not in inventory['Windows']['children']:
                        inventory['Windows']['children'].append(host[os_field])
            elif ("Linux" in host[os_field]) or ("Red Hat" in host[os_field]) or ("Debian" in host[os_field]):
                if host[os_field] not in inventory['Linux']['children']:
                        inventory['Linux']['children'].append(host[os_field])
            elif ("Cisco" in host[os_field]) or ("Catalyst" in host[os_field]):
                if host[os_field] not in inventory['Network']['children']:
                        inventory['Network']['children'].append(host[os_field])
            else:
                if host[os_field] not in inventory['Other']['children']:
                        inventory['Other']['children'].append(host[os_field])
        return inventory

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