"""Application tools: SES, Pinpoint, Amplify, MediaConvert, Location, IoT Core, Connect."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateSESIdentityTool(BaseTool):
    name = "create_ses_identity"
    description = "Create an Amazon SES email identity for sending transactional emails."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {
            "ses_id": {"type": "string"}, "label": {"type": "string"},
            "email_or_domain": {"type": "string", "description": "Email address or domain to verify."},
        },
        "required": ["ses_id", "label", "email_or_domain"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["ses_id"]
        identity = params["email_or_domain"]
        is_domain = "@" not in identity
        if is_domain:
            tf_code = f'''resource "aws_ses_domain_identity" "{sid}" {{
  domain = "{identity}"
}}
'''
        else:
            tf_code = f'''resource "aws_ses_email_identity" "{sid}" {{
  email = "{identity}"
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_ses", label=params.get("label", sid), config=ToolNodeConfig()),
            terraform_code={"application.tf": tf_code},
        )


class CreatePinpointAppTool(BaseTool):
    name = "create_pinpoint_app"
    description = "Create an Amazon Pinpoint application for push notifications and targeted messaging."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {
            "pinpoint_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["pinpoint_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["pinpoint_id"]
        tf_code = f'''resource "aws_pinpoint_app" "{pid}" {{
  name = "${{var.project_name}}-{pid}"
  tags = {{ Name = "${{var.project_name}}-{pid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=pid, type="aws_pinpoint", label=params.get("label", pid), config=ToolNodeConfig()),
            terraform_code={"application.tf": tf_code},
        )


class CreateAmplifyAppTool(BaseTool):
    name = "create_amplify_app"
    description = "Create an AWS Amplify app for full-stack web and mobile app hosting."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {
            "amplify_id": {"type": "string"}, "label": {"type": "string"},
            "repository": {"type": "string", "description": "Git repository URL.", "default": ""},
            "framework": {"type": "string", "default": "React"},
        },
        "required": ["amplify_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        aid = params["amplify_id"]
        tf_code = f'''resource "aws_amplify_app" "{aid}" {{
  name = "${{var.project_name}}-{aid}"
  {"repository = \"" + params['repository'] + '"' if params.get('repository') else ""}
  platform = "WEB"
  tags = {{ Name = "${{var.project_name}}-{aid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=aid, type="aws_amplify", label=params.get("label", aid), config=ToolNodeConfig()),
            terraform_code={"application.tf": tf_code},
        )


class CreateMediaConvertJobTool(BaseTool):
    name = "create_media_convert_job"
    description = "Create an AWS Elemental MediaConvert queue for video processing and transcoding."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {
            "mc_id": {"type": "string"}, "label": {"type": "string"},
            "pricing_plan": {"type": "string", "default": "ON_DEMAND"},
        },
        "required": ["mc_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        mid = params["mc_id"]
        tf_code = f'''resource "aws_media_convert_queue" "{mid}" {{
  name         = "${{var.project_name}}-{mid}"
  pricing_plan = "{params.get('pricing_plan', 'ON_DEMAND')}"
  tags = {{ Name = "${{var.project_name}}-{mid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=mid, type="aws_mediaconvert", label=params.get("label", mid), config=ToolNodeConfig()),
            terraform_code={"application.tf": tf_code},
        )


class CreateLocationTrackerTool(BaseTool):
    name = "create_location_tracker"
    description = "Create an Amazon Location Service tracker for device location tracking."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {
            "tracker_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["tracker_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["tracker_id"]
        tf_code = f'''resource "aws_location_tracker" "{tid}" {{
  tracker_name = "${{var.project_name}}-{tid}"
  tags = {{ Name = "${{var.project_name}}-{tid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_location", label=params.get("label", tid), config=ToolNodeConfig()),
            terraform_code={"application.tf": tf_code},
        )


class CreateIoTThingTool(BaseTool):
    name = "create_iot_thing"
    description = "Create an AWS IoT Core thing for IoT device management."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {
            "iot_id": {"type": "string"}, "label": {"type": "string"},
            "thing_type": {"type": "string", "default": ""},
        },
        "required": ["iot_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        iid = params["iot_id"]
        tf_code = f'''resource "aws_iot_thing" "{iid}" {{
  name = "${{var.project_name}}-{iid}"
}}
'''
        return ToolResult(
            node=ToolNode(id=iid, type="aws_iot", label=params.get("label", iid), config=ToolNodeConfig()),
            terraform_code={"application.tf": tf_code},
        )


class CreateConnectInstanceTool(BaseTool):
    name = "create_connect_instance"
    description = "Create an Amazon Connect instance for cloud contact center."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {
            "connect_id": {"type": "string"}, "label": {"type": "string"},
            "identity_management_type": {"type": "string", "default": "CONNECT_MANAGED"},
        },
        "required": ["connect_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["connect_id"]
        tf_code = f'''resource "aws_connect_instance" "{cid}" {{
  instance_alias            = "${{var.project_name}}-{cid}"
  identity_management_type  = "{params.get('identity_management_type', 'CONNECT_MANAGED')}"
  inbound_calls_enabled     = true
  outbound_calls_enabled    = true
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_connect", label=params.get("label", cid), config=ToolNodeConfig()),
            terraform_code={"application.tf": tf_code},
        )
