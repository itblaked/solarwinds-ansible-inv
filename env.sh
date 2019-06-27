#!/bin/bash

export NPM_PAYLOAD="query=SELECT CP.Asset_Group as Asset_Group, SysName, DNS, NodeID, MachineType, CP.AppOwner, CP.Responsible_Teams, CP.Environment FROM Orion.Nodes as N JOIN Orion.NodesCustomProperties as CP on N.NodeID = CP.NodeID WHERE CP.Asset_Group != '' AND N.SysName != '' AND N.DNS != '' AND N.MachineType != '' AND CP.AppOwner != '' AND CP.Environment != '' AND CP.Responsible_Teams != ''"
export NPM_HOSTNAME="DNS"
export NPM_PRIMARY_GROUP="Asset_Group"
export NPM_SECONDARY_GROUP="MachineType"
