"""Create CloudFront Distribution tool — provisions via boto3."""
import time
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateCloudFrontDistributionTool(BaseTool):
    name = "create_cloudfront_distribution"
    description = "Create an Amazon CloudFront CDN distribution for content delivery and caching."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "cf_id": {"type": "string"}, "label": {"type": "string"},
            "origin_domain": {"type": "string", "description": "Origin domain name or S3 bucket domain."},
            "default_ttl": {"type": "integer", "description": "Default cache TTL in seconds.", "default": 86400},
            "price_class": {"type": "string", "default": "PriceClass_100"},
        },
        "required": ["cf_id", "label", "origin_domain"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cf_id"]
        label = params.get("label", cid)
        origin = params["origin_domain"]
        caller_ref = f"__PROJECT__-{cid}-{int(time.time())}"
        configs = [{
            "service": "cloudfront",
            "action": "create_distribution",
            "params": {
                "DistributionConfig": {
                    "CallerReference": caller_ref,
                    "Comment": f"__PROJECT__-{cid}",
                    "Enabled": True,
                    "DefaultRootObject": "index.html",
                    "PriceClass": params.get("price_class", "PriceClass_100"),
                    "Origins": {
                        "Quantity": 1,
                        "Items": [{
                            "Id": f"{cid}-origin",
                            "DomainName": origin,
                            "CustomOriginConfig": {
                                "HTTPPort": 80,
                                "HTTPSPort": 443,
                                "OriginProtocolPolicy": "https-only",
                            },
                        }],
                    },
                    "DefaultCacheBehavior": {
                        "TargetOriginId": f"{cid}-origin",
                        "ViewerProtocolPolicy": "redirect-to-https",
                        "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                        "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                        "DefaultTTL": params.get("default_ttl", 86400),
                        "ForwardedValues": {
                            "QueryString": False,
                            "Cookies": {"Forward": "none"},
                        },
                    },
                    "ViewerCertificate": {"CloudFrontDefaultCertificate": True},
                    "Restrictions": {"GeoRestriction": {"RestrictionType": "none", "Quantity": 0}},
                },
                "Tags": {"Items": [{"Key": "Name", "Value": f"__PROJECT__-{cid}"}]},
            },
            "label": label,
            "resource_type": "aws_cloudfront",
            "resource_id_path": "Distribution.Id",
            "delete_action": "delete_distribution",
            "delete_params_key": "Id",
        }]
        return ToolResult(
            node=ToolNode(id=cid, type="aws_cloudfront", label=label,
                          config=ToolNodeConfig(extra={"origin_domain": origin})),
            boto3_config={"cloudfront": configs},
        )
