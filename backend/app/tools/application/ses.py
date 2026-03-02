"""Application tools: SES, Pinpoint, Amplify, MediaConvert, Location, IoT Core, Connect — provisions via boto3."""
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
        label = params.get("label", sid)
        identity = params["email_or_domain"]
        is_domain = "@" not in identity

        if is_domain:
            configs = [{
                "service": "sesv2",
                "action": "create_email_identity",
                "params": {"EmailIdentity": identity, "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}]},
                "label": label,
                "resource_type": "aws_ses_domain",
                "resource_id_path": "IdentityType",
                "delete_action": "delete_email_identity",
                "delete_params": {"EmailIdentity": identity},
            }]
        else:
            configs = [{
                "service": "sesv2",
                "action": "create_email_identity",
                "params": {"EmailIdentity": identity, "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}]},
                "label": label,
                "resource_type": "aws_ses_email",
                "resource_id_path": "IdentityType",
                "delete_action": "delete_email_identity",
                "delete_params": {"EmailIdentity": identity},
            }]

        return ToolResult(
            node=ToolNode(id=sid, type="aws_ses", label=label, config=ToolNodeConfig()),
            boto3_config={"sesv2": configs},
        )


class CreatePinpointAppTool(BaseTool):
    name = "create_pinpoint_app"
    description = "Create an Amazon Pinpoint application for push notifications and targeted messaging."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {"pinpoint_id": {"type": "string"}, "label": {"type": "string"}},
        "required": ["pinpoint_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["pinpoint_id"]
        label = params.get("label", pid)
        configs = [{
            "service": "pinpoint",
            "action": "create_app",
            "params": {"CreateApplicationRequest": {"Name": f"__PROJECT__-{pid}", "tags": {"Name": f"__PROJECT__-{pid}"}}},
            "label": label,
            "resource_type": "aws_pinpoint",
            "resource_id_path": "ApplicationResponse.Id",
            "delete_action": "delete_app",
            "delete_params_key": "ApplicationId",
        }]
        return ToolResult(
            node=ToolNode(id=pid, type="aws_pinpoint", label=label, config=ToolNodeConfig()),
            boto3_config={"pinpoint": configs},
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
        label = params.get("label", aid)
        create_params: dict[str, Any] = {
            "name": f"__PROJECT__-{aid}",
            "platform": "WEB",
            "tags": {"Name": f"__PROJECT__-{aid}"},
        }
        if params.get("repository"):
            create_params["repository"] = params["repository"]
        configs = [{
            "service": "amplify",
            "action": "create_app",
            "params": create_params,
            "label": label,
            "resource_type": "aws_amplify",
            "resource_id_path": "app.appId",
            "delete_action": "delete_app",
            "delete_params_key": "appId",
        }]
        return ToolResult(
            node=ToolNode(id=aid, type="aws_amplify", label=label, config=ToolNodeConfig()),
            boto3_config={"amplify": configs},
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
        label = params.get("label", mid)
        configs = [{
            "service": "mediaconvert",
            "action": "create_queue",
            "params": {
                "Name": f"__PROJECT__-{mid}",
                "PricingPlan": params.get("pricing_plan", "ON_DEMAND"),
                "Tags": {"Name": f"__PROJECT__-{mid}"},
            },
            "label": label,
            "resource_type": "aws_mediaconvert",
            "resource_id_path": "Queue.Arn",
            "delete_action": "delete_queue",
            "delete_params": {"Name": f"__PROJECT__-{mid}"},
        }]
        return ToolResult(
            node=ToolNode(id=mid, type="aws_mediaconvert", label=label, config=ToolNodeConfig()),
            boto3_config={"mediaconvert": configs},
        )


class CreateLocationTrackerTool(BaseTool):
    name = "create_location_tracker"
    description = "Create an Amazon Location Service tracker for device location tracking."
    category = "application"
    parameters = {
        "type": "object",
        "properties": {"tracker_id": {"type": "string"}, "label": {"type": "string"}},
        "required": ["tracker_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["tracker_id"]
        label = params.get("label", tid)
        configs = [{
            "service": "location",
            "action": "create_tracker",
            "params": {
                "TrackerName": f"__PROJECT__-{tid}",
                "Tags": {"Name": f"__PROJECT__-{tid}"},
            },
            "label": label,
            "resource_type": "aws_location_tracker",
            "resource_id_path": "TrackerName",
            "delete_action": "delete_tracker",
            "delete_params": {"TrackerName": f"__PROJECT__-{tid}"},
        }]
        return ToolResult(
            node=ToolNode(id=tid, type="aws_location", label=label, config=ToolNodeConfig()),
            boto3_config={"location": configs},
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
        label = params.get("label", iid)
        create_params: dict[str, Any] = {"thingName": f"__PROJECT__-{iid}"}
        if params.get("thing_type"):
            create_params["thingTypeName"] = params["thing_type"]
        configs = [{
            "service": "iot",
            "action": "create_thing",
            "params": create_params,
            "label": label,
            "resource_type": "aws_iot_thing",
            "resource_id_path": "thingName",
            "delete_action": "delete_thing",
            "delete_params": {"thingName": f"__PROJECT__-{iid}"},
        }]
        return ToolResult(
            node=ToolNode(id=iid, type="aws_iot", label=label, config=ToolNodeConfig()),
            boto3_config={"iot": configs},
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
        label = params.get("label", cid)
        configs = [{
            "service": "connect",
            "action": "create_instance",
            "params": {
                "InstanceAlias": f"__PROJECT__-{cid}",
                "IdentityManagementType": params.get("identity_management_type", "CONNECT_MANAGED"),
                "InboundCallsEnabled": True,
                "OutboundCallsEnabled": True,
            },
            "label": label,
            "resource_type": "aws_connect",
            "resource_id_path": "Id",
            "delete_action": "delete_instance",
            "delete_params_key": "InstanceId",
        }]
        return ToolResult(
            node=ToolNode(id=cid, type="aws_connect", label=label, config=ToolNodeConfig()),
            boto3_config={"connect": configs},
        )
