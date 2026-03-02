"""Create S3 Bucket tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateS3BucketTool(BaseTool):
    name = "create_s3_bucket"
    description = "Create an Amazon S3 bucket for object storage with versioning, encryption, and access control."
    category = "storage"
    parameters = {
        "type": "object",
        "properties": {
            "bucket_id": {"type": "string"},
            "label": {"type": "string"},
            "versioning": {"type": "boolean", "default": True},
            "encryption": {"type": "string", "description": "'AES256' or 'aws:kms'.", "default": "AES256"},
            "block_public_access": {"type": "boolean", "default": True},
        },
        "required": ["bucket_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["bucket_id"]
        label = params.get("label", bid)
        versioning = params.get("versioning", True)
        encryption = params.get("encryption", "AES256")
        block_public = params.get("block_public_access", True)

        configs = [
            {
                "service": "s3",
                "action": "create_bucket",
                "params": {
                    "Bucket": f"__PROJECT__-{bid}",
                    "CreateBucketConfiguration": {"LocationConstraint": "__REGION__"},
                },
                "label": label,
                "resource_type": "aws_s3_bucket",
                "resource_id_path": "Location",
                "delete_action": "delete_bucket",
                "delete_params": {"Bucket": f"__PROJECT__-{bid}"},
            },
            {
                "service": "s3",
                "action": "put_bucket_versioning",
                "params": {
                    "Bucket": f"__PROJECT__-{bid}",
                    "VersioningConfiguration": {"Status": "Enabled" if versioning else "Suspended"},
                },
                "label": f"{label} — Versioning",
                "resource_type": "aws_s3_bucket_versioning",
                "is_support": True,
            },
            {
                "service": "s3",
                "action": "put_bucket_encryption",
                "params": {
                    "Bucket": f"__PROJECT__-{bid}",
                    "ServerSideEncryptionConfiguration": {
                        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": encryption}}],
                    },
                },
                "label": f"{label} — Encryption",
                "resource_type": "aws_s3_bucket_encryption",
                "is_support": True,
            },
        ]

        if block_public:
            configs.append({
                "service": "s3",
                "action": "put_public_access_block",
                "params": {
                    "Bucket": f"__PROJECT__-{bid}",
                    "PublicAccessBlockConfiguration": {
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": True,
                        "RestrictPublicBuckets": True,
                    },
                },
                "label": f"{label} — Public Access Block",
                "resource_type": "aws_s3_public_access_block",
                "is_support": True,
            })

        return ToolResult(
            node=ToolNode(id=bid, type="aws_s3", label=label,
                          config=ToolNodeConfig(extra={"versioning": versioning})),
            boto3_config={"s3": configs},
        )
