"""Create CloudFront Distribution tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateCloudFrontDistributionTool(BaseTool):
    name = "create_cloudfront_distribution"
    description = "Create an Amazon CloudFront CDN distribution for content delivery and caching."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "cf_id": {"type": "string"},
            "label": {"type": "string"},
            "origin_domain": {"type": "string", "description": "Origin domain name or S3 bucket domain."},
            "default_ttl": {"type": "integer", "description": "Default cache TTL in seconds.", "default": 86400},
            "price_class": {"type": "string", "default": "PriceClass_100"},
        },
        "required": ["cf_id", "label", "origin_domain"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cf_id"]
        origin = params["origin_domain"]
        tf_code = f'''resource "aws_cloudfront_distribution" "{cid}" {{
  enabled             = true
  default_root_object = "index.html"
  price_class         = "{params.get('price_class', 'PriceClass_100')}"

  origin {{
    domain_name = "{origin}"
    origin_id   = "{cid}-origin"
  }}

  default_cache_behavior {{
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "{cid}-origin"
    viewer_protocol_policy = "redirect-to-https"
    default_ttl            = {params.get('default_ttl', 86400)}

    forwarded_values {{
      query_string = false
      cookies {{ forward = "none" }}
    }}
  }}

  restrictions {{
    geo_restriction {{ restriction_type = "none" }}
  }}

  viewer_certificate {{
    cloudfront_default_certificate = true
  }}

  tags = {{ Name = "${{var.project_name}}-{cid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_cloudfront", label=params.get("label", cid),
                          config=ToolNodeConfig(extra={"origin_domain": origin})),
            terraform_code={"networking.tf": tf_code},
        )
