#!/bin/bash

export NPM_PAYLOAD="query=SELECT CP.Asset_Group as Asset_Group, SysName, DNS, NodeID, MachineType, CP.AppOwner, CP.Responsible_Teams, CP.Environment FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID WHERE CP.Asset_Group != '' AND N.SysName != '' AND N.DNS != '' AND N.MachineType != '' AND CP.AppOwner != '' AND CP.Environment != '' AND CP.Responsible_Teams != ''"
export NPM_GROUP_PAYLOAD="query=SELECT CP.Asset_Group as Asset_Group, N.MachineType as ChildGroupName FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID WHERE CP.Asset_Group != '' AND N.SysName != '' AND N.DNS != '' AND N.MachineType != '' AND CP.AppOwner != '' AND CP.Environment != '' AND CP.Responsible_Teams != ''"
export NPM_GROUPFIELD="Asset_Group"
export NPM_HOSTFIELD="DNS"
export NPM_USE_GROUPS="true"
export NPM_PARENTFIELD="Asset_Group"
export NPM_CHILDFIELD="ChildGroupName"
