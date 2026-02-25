"""Create S3 Bucket tool."""
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
        tf_code = f'''resource "aws_s3_bucket" "{bid}" {{
  bucket = "${{var.project_name}}-{bid}"
  tags   = {{ Name = "${{var.project_name}}-{bid}" }}
}}

resource "aws_s3_bucket_versioning" "{bid}_versioning" {{
  bucket = aws_s3_bucket.{bid}.id
  versioning_configuration {{ status = "{('Enabled' if params.get('versioning', True) else 'Disabled')}" }}
}}

resource "aws_s3_bucket_server_side_encryption_configuration" "{bid}_enc" {{
  bucket = aws_s3_bucket.{bid}.id
  rule {{
    apply_server_side_encryption_by_default {{ sse_algorithm = "{params.get('encryption', 'AES256')}" }}
  }}
}}

resource "aws_s3_bucket_public_access_block" "{bid}_pab" {{
  bucket                  = aws_s3_bucket.{bid}.id
  block_public_acls       = {str(params.get('block_public_access', True)).lower()}
  block_public_policy     = {str(params.get('block_public_access', True)).lower()}
  ignore_public_acls      = {str(params.get('block_public_access', True)).lower()}
  restrict_public_buckets = {str(params.get('block_public_access', True)).lower()}
}}
'''
        return ToolResult(
            node=ToolNode(id=bid, type="aws_s3", label=params.get("label", bid),
                          config=ToolNodeConfig(extra={"versioning": params.get("versioning", True)})),
            terraform_code={"storage.tf": tf_code},
        )
