"""Create Direct Connect, Transit Gateway, NAT Gateway, Elastic IP, Global Accelerator tools."""
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
        tf_code = f'''resource "aws_dx_connection" "{did}" {{
  name      = "${{var.project_name}}-{did}"
  bandwidth = "{params.get('bandwidth', '1Gbps')}"
  location  = "{params.get('location', 'EqDC2')}"
  tags = {{ Name = "${{var.project_name}}-{did}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=did, type="aws_direct_connect", label=params.get("label", did),
                          config=ToolNodeConfig(extra={"bandwidth": params.get("bandwidth", "1Gbps")})),
            terraform_code={"networking.tf": tf_code},
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
        tf_code = f'''resource "aws_ec2_transit_gateway" "{tid}" {{
  description = "${{var.project_name}}-{tid}"
  amazon_side_asn = {params.get('amazon_asn', 64512)}
  tags = {{ Name = "${{var.project_name}}-{tid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_transit_gateway", label=params.get("label", tid), config=ToolNodeConfig()),
            terraform_code={"networking.tf": tf_code},
        )


class CreateNatGatewayTool(BaseTool):
    name = "create_nat_gateway"
    description = "Create a standalone NAT Gateway for outbound internet from private subnets."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "nat_id": {"type": "string"}, "label": {"type": "string"},
            "subnet_ref": {"type": "string", "description": "Terraform reference for the public subnet.", "default": "aws_subnet.public_0.id"},
        },
        "required": ["nat_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        nid = params["nat_id"]
        tf_code = f'''resource "aws_eip" "{nid}_eip" {{ domain = "vpc" }}

resource "aws_nat_gateway" "{nid}" {{
  allocation_id = aws_eip.{nid}_eip.id
  subnet_id     = {params.get('subnet_ref', 'aws_subnet.public_0.id')}
  tags = {{ Name = "${{var.project_name}}-{nid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=nid, type="aws_nat_gateway", label=params.get("label", nid), config=ToolNodeConfig()),
            terraform_code={"networking.tf": tf_code},
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
        tf_code = f'''resource "aws_eip" "{eid}" {{
  domain = "vpc"
  tags = {{ Name = "${{var.project_name}}-{eid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=eid, type="aws_elastic_ip", label=params.get("label", eid), config=ToolNodeConfig()),
            terraform_code={"networking.tf": tf_code},
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
        tf_code = f'''resource "aws_globalaccelerator_accelerator" "{gid}" {{
  name            = "${{var.project_name}}-{gid}"
  ip_address_type = "IPV4"
  enabled         = true
  attributes {{
    flow_logs_enabled = {str(params.get('flow_logs_enabled', False)).lower()}
  }}
}}
'''
        return ToolResult(
            node=ToolNode(id=gid, type="aws_global_accelerator", label=params.get("label", gid), config=ToolNodeConfig()),
            terraform_code={"networking.tf": tf_code},
        )
