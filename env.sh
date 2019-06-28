#!/bin/bash

# SWSQL query to send to SolarWinds via REST API
export NPM_PAYLOAD="query=SELECT CP.Asset_Group as Asset_Group, SysName, DNS, IP, NodeID, MachineType, CP.AppOwner, CP.Responsible_Teams, CP.Environment, CP.APP_Group, CP.APP_Group1, CP.APP_Group2, CP.APP_Group3, CP.Asset_Category, CP.Loc1_SiteCode, CP.Loc2_Region, CP.Loc3_Country FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID WHERE CP.Asset_Group != '' AND N.SysName != '' AND N.DNS != '' AND N.MachineType != '' AND CP.AppOwner != '' AND CP.Responsible_Teams != '' AND CP.APP_Group != ''"
# Field in query results to use for hostname
# e.g. "DNS"
export NPM_HOSTNAME_FIELD="DNS"
# Field in query results that contains Operating System
# e.g. "MachineType"
export NPM_OS_FIELD="MachineType"
# comma-separated list of fields from query results to create and add hosts to as groups - these should NOT be NULL, ensure via payload query
# e.g. NPM_GROUP_ON_FIELDS="Asset_Group,MachineType"
export NPM_GROUP_ON_FIELDS=""
# comma-separated list of fields from query results to map to host variables - these should match columns defined in the payload query 
# e.g. NPM_HOSTVAR_FIELDS="Asset_Group,SysName,DNS,IP,NodeID,MachineType,AppOwner,Responsible_Teams,Environment,APP_Group,APP_Group3,APP_Group2,APP_Group3,Asset_Category,Loc1_SiteCode,Loc2_Region,Loc3_Country"
export NPM_HOSTVAR_FIELDS=""