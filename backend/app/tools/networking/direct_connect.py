"""Networking tools: Direct Connect, Transit Gateway, NAT Gateway, Elastic IP, Global Accelerator — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateDirectConnectTool(BaseTool):
    name = "create_direct_connect"
    description = "Create an AWS Direct Connect connection for dedicated network link between on-premises and AWS."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "dc_id": {"type": "string"}, "label": {"type": "string"},
            "bandwidth": {"type": "string", "default": "1Gbps"},
            "location": {"type": "string", "description": "Direct Connect location.", "default": "EqDC2"},
        },
        "required": ["dc_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        did = params["dc_id"]
        label = params.get("label", did)
        configs = [{
            "service": "directconnect",
            "action": "create_connection",
            "params": {
                "connectionName": f"__PROJECT__-{did}",
                "bandwidth": params.get("bandwidth", "1Gbps"),
                "location": params.get("location", "EqDC2"),
                "tags": [{"key": "Name", "value": f"__PROJECT__-{did}"}],
            },
            "label": label,
            "resource_type": "aws_direct_connect",
            "resource_id_path": "connectionId",
            "delete_action": "delete_connection",
            "delete_params_key": "connectionId",
        }]
        return ToolResult(
            node=ToolNode(id=did, type="aws_direct_connect", label=label,
                          config=ToolNodeConfig(extra={"bandwidth": params.get("bandwidth", "1Gbps")})),
            boto3_config={"directconnect": configs},
        )


class CreateTransitGatewayTool(BaseTool):
    name = "create_transit_gateway"
    description = "Create an AWS Transit Gateway for connecting multiple VPCs and on-premises networks."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "tgw_id": {"type": "string"}, "label": {"type": "string"},
            "amazon_asn": {"type": "integer", "default": 64512},
        },
        "required": ["tgw_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["tgw_id"]
        label = params.get("label", tid)
        configs = [{
            "service": "ec2",
            "action": "create_transit_gateway",
            "params": {
                "Description": f"__PROJECT__-{tid}",
                "Options": {"AmazonSideAsn": params.get("amazon_asn", 64512), "AutoAcceptSharedAttachments": "enable"},
                "TagSpecifications": [{"ResourceType": "transit-gateway", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{tid}"}]}],
            },
            "label": label,
            "resource_type": "aws_transit_gateway",
            "resource_id_path": "TransitGateway.TransitGatewayId",
            "delete_action": "delete_transit_gateway",
            "delete_params_key": "TransitGatewayId",
        }]
        return ToolResult(
            node=ToolNode(id=tid, type="aws_transit_gateway", label=label, config=ToolNodeConfig()),
            boto3_config={"ec2": configs},
        )


class CreateNatGatewayTool(BaseTool):
    name = "create_nat_gateway"
    description = "Create a standalone NAT Gateway for outbound internet from private subnets."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "nat_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["nat_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        nid = params["nat_id"]
        label = params.get("label", nid)
        configs = [
            {
                "service": "ec2",
                "action": "allocate_address",
                "params": {"Domain": "vpc"},
                "label": f"{label} — EIP",
                "resource_type": "aws_eip",
                "resource_id_path": "AllocationId",
                "delete_action": "release_address",
                "delete_params_key": "AllocationId",
            },
            {
                "service": "ec2",
                "action": "create_nat_gateway",
                "params": {
                    "AllocationId": "__RESOLVE_PREV__",
                    "SubnetId": "__FIRST_PUBLIC_SUBNET__",
                    "TagSpecifications": [{"ResourceType": "natgateway", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{nid}"}]}],
                },
                "label": label,
                "resource_type": "aws_nat_gateway",
                "resource_id_path": "NatGateway.NatGatewayId",
                "delete_action": "delete_nat_gateway",
                "delete_params_key": "NatGatewayId",
            },
        ]
        return ToolResult(
            node=ToolNode(id=nid, type="aws_nat_gateway", label=label, config=ToolNodeConfig()),
            boto3_config={"ec2": configs},
        )


class CreateElasticIPTool(BaseTool):
    name = "create_elastic_ip"
    description = "Allocate an AWS Elastic IP address."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "eip_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["eip_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        eid = params["eip_id"]
        label = params.get("label", eid)
        configs = [{
            "service": "ec2",
            "action": "allocate_address",
            "params": {
                "Domain": "vpc",
                "TagSpecifications": [{"ResourceType": "elastic-ip", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{eid}"}]}],
            },
            "label": label,
            "resource_type": "aws_elastic_ip",
            "resource_id_path": "AllocationId",
            "delete_action": "release_address",
            "delete_params_key": "AllocationId",
        }]
        return ToolResult(
            node=ToolNode(id=eid, type="aws_elastic_ip", label=label, config=ToolNodeConfig()),
            boto3_config={"ec2": configs},
        )


class CreateGlobalAcceleratorTool(BaseTool):
    name = "create_global_accelerator"
    description = "Create an AWS Global Accelerator for improved global application availability and performance."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "ga_id": {"type": "string"}, "label": {"type": "string"},
            "flow_logs_enabled": {"type": "boolean", "default": False},
        },
        "required": ["ga_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        gid = params["ga_id"]
        label = params.get("label", gid)
        configs = [{
            "service": "globalaccelerator",
            "action": "create_accelerator",
            "params": {
                "Name": f"__PROJECT__-{gid}",
                "IpAddressType": "IPV4",
                "Enabled": True,
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{gid}"}],
            },
            "label": label,
            "resource_type": "aws_global_accelerator",
            "resource_id_path": "Accelerator.AcceleratorArn",
            "delete_action": "delete_accelerator",
            "delete_params_key": "AcceleratorArn",
        }]
        return ToolResult(
            node=ToolNode(id=gid, type="aws_global_accelerator", label=label, config=ToolNodeConfig()),
            boto3_config={"globalaccelerator": configs},
        )
