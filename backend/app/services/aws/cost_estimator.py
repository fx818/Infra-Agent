"""
AWS Cost Estimator — static pricing data for cost estimation.
"""

# ── AWS Pricing Tables (US East, On-Demand, Monthly) ─────────────────
# These are approximate reference prices used by the CostAgent.

AWS_PRICING: dict[str, dict] = {
    "aws_lambda": {
        "description": "AWS Lambda — Serverless compute",
        "unit": "per 1M requests + GB-seconds",
        "price_per_million_requests": 0.20,
        "price_per_gb_second": 0.0000166667,
        "free_tier": {"requests": 1_000_000, "gb_seconds": 400_000},
    },
    "aws_apigatewayv2": {
        "description": "API Gateway v2 (HTTP API)",
        "unit": "per 1M requests",
        "price_per_million_requests": 1.00,
        "free_tier": {"requests": 1_000_000},  # First 12 months
    },
    "aws_dynamodb": {
        "description": "DynamoDB — On-Demand",
        "unit": "per 1M request units",
        "price_per_million_wcu": 1.25,
        "price_per_million_rcu": 0.25,
        "storage_per_gb": 0.25,
    },
    "aws_sqs": {
        "description": "SQS — Simple Queue Service",
        "unit": "per 1M requests",
        "price_per_million_standard": 0.40,
        "price_per_million_fifo": 0.50,
        "free_tier": {"requests": 1_000_000},
    },
    "aws_ecs": {
        "description": "ECS Fargate",
        "unit": "per vCPU-hour + GB-hour",
        "price_per_vcpu_hour": 0.04048,
        "price_per_gb_hour": 0.004445,
    },
    "aws_rds": {
        "description": "RDS — Relational Database Service",
        "unit": "per instance-hour",
        "instances": {
            "db.t3.micro": 0.017,
            "db.t3.small": 0.034,
            "db.t3.medium": 0.068,
            "db.t3.large": 0.136,
            "db.r5.large": 0.250,
            "db.r5.xlarge": 0.500,
        },
        "storage_per_gb": 0.115,
    },
    "aws_elasticache": {
        "description": "ElastiCache (Redis)",
        "unit": "per node-hour",
        "instances": {
            "cache.t3.micro": 0.017,
            "cache.t3.small": 0.034,
            "cache.t3.medium": 0.068,
            "cache.r5.large": 0.228,
        },
    },
    "aws_s3": {
        "description": "S3 — Simple Storage Service",
        "unit": "per GB stored + requests",
        "storage_per_gb": 0.023,
        "put_per_1000": 0.005,
        "get_per_1000": 0.0004,
        "free_tier": {"storage_gb": 5, "put_requests": 2000, "get_requests": 20000},
    },
    "aws_cloudfront": {
        "description": "CloudFront CDN",
        "unit": "per GB transferred + requests",
        "transfer_per_gb_first_10tb": 0.085,
        "requests_per_10000": 0.01,
        "free_tier": {"transfer_gb": 1, "requests": 10_000_000},
    },
    "aws_vpc": {
        "description": "VPC — NAT Gateway",
        "unit": "per hour + per GB processed",
        "nat_gateway_per_hour": 0.045,
        "nat_gateway_per_gb": 0.045,
    },
    "aws_route53": {
        "description": "Route 53 DNS",
        "unit": "per hosted zone + queries",
        "per_hosted_zone": 0.50,
        "per_million_queries": 0.40,
    },
    "aws_sns": {
        "description": "SNS — Simple Notification Service",
        "unit": "per 1M publishes",
        "price_per_million": 0.50,
        "free_tier": {"publishes": 1_000_000},
    },
}
