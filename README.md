# solarwinds-dynamic-inventory

Python inventory script to be used with Ansible Engine and Ansible Tower to pull host information out of SolarWinds.

It originates from https://github.com/cbabs/solarwinds-ansible-inv but has been modified.

## Usage
`solarwinds.py` is a python script that can be executed on any host with python installed. It responds to --list and --host arguments. Variables can be set in the environment to define the behavior of this script, see  VARIABLES below.

`solarwinds.ini` is the configuration file where servername, username and password are contained. This file must be in the same directory as `solarwinds.py`. 
 
## Variables
The following variables determine how the script will assemble the retrieved SolarWinds data into hosts, groups and host variables.

### SW_QUERY
This is the SWSQL query to send to the SolarWinds REST API endpoint. This should be a valid query that can be executed in a tool like SWSQL Studio.
e.g. `SW_QUERY="SELECT CP.Asset_Group as Asset_Group, SysName, DNS, IP, MachineType FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID"`

### SW_HOSTNAME_FIELD
Field in the query results to use for hostname. This will be mapped to a hostvariable `ansible_host`. This should be something reachable on the network like "DNS", "SysName" or "IP"
e.g. `SW_HOSTNAME_FIELD="DNS"`

### SW_CATEGORY_FIELD
The field in the query to use to map the host to an category groups (defined in the variable `SW_CATEGORIES`). This is likely a field such as "MachineType"
e.g. `SW_CATEGORY_FIELD="MachineType"`

### SW_GROUP_ON_FIELDS
Comma-separated list of fields from query results to create and add hosts to as groups - these should NOT be NULL, ensure via query. If no groups should be created, this should be an empty string or False.
e.g. `SW_GROUP_ON_FIELDS="Asset_Group,MachineType"`

### SW_HOSTVAR_FIELDS
Comma-separated list of fields from query results to map to host variables - these should match columns defined in the query. If no host variables should be mapped, this should be an empty string or False.
e.g. `SW_HOSTVAR_FIELDS="SysName,DNS,IP,NodeID,MachineType,Environment"`

### SW_CATEGORIES
List of categories and strings used to match against `category_field`. Any fields not matched will be placed in a category defined with no matching strings. In order to facilitate converting this environment variable into a Python data structure, it should be entered as follows:

`Category1:Comma,Separated,Strings; Category2:Unique,Matches; Category3:More; Other:`

In this case there will be 4 total Categories as follows:
Category1 - Any hosts with `category_field` matching one of the strings 'Comma', 'Separated', or 'Strings' will be placed here
Category2 - Any hosts with `category_field` matching one of the strings 'Unique', or 'Matches' will be placed here
Category3 - Any hosts with `category_field` matching 'More' will be placed here
Other - Any hosts not matching one of the previously defined 3 categories will default into this category - this should NOT contain any strings to match, representing an unmatched category.

e.g. `SW_CATEGORIES="Windows:Windows;Linux:Linux,Red Hat,Debian;Network:Cisco,Catalyst;Other:"`

## Ansible Tower
To use this in Tower, create a credential type with the following:

Input Configuration:
```
fields:
  - type: string
    id: sw_server
    label: SolarWinds Host
  - type: string
    id: sw_username
    label: Username
  - secret: true
    type: string
    id: sw_password
    label: Password
required:
  - sw_server
  - sw_username
  - sw_password
```

Injector Configuration:
```
env:
  SW_INI_FILE: '{{tower.filename}}'
file:
  template: |-
    [solarwinds]
    sw_server = {{sw_server}}
    sw_user = {{sw_username}}
    sw_password = {{sw_password}}
```

Next, create a credential of this type.

Create an inventory source using this credential and specify the required variables as environment variables.

This should probably be an inventory plugin instead of a script.

## Tested On
* Orion Platform 2018.2 HF3
* ansible-2.7.10-1.el7ae.noarch
* ansible-tower-server-3.4.3-1.el7.x86_64
* Python 2.7.5 (default, Mar 26 2019, 22:13:06)
* [GCC 4.8.5 20150623 (Red Hat 4.8.5-36)] on linux2
