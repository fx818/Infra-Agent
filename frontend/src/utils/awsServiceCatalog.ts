/**
 * Full catalog of AWS services available for drag-and-drop.
 * Each entry maps to a backend tool and has metadata for the toolbar.
 */

export interface AwsServiceDef {
    id: string;           // e.g. "aws_ec2"
    name: string;         // display name
    category: string;     // Compute, Storage, Database, ...
    description: string;  // one-liner
    defaultConfig: Record<string, string>;
}

export const AWS_CATEGORIES = [
    'Compute',
    'Storage',
    'Database',
    'Networking',
    'Messaging',
    'Security',
    'Monitoring',
    'DevOps',
    'Analytics',
] as const;

export type AwsCategory = typeof AWS_CATEGORIES[number];

export const CATEGORY_COLORS: Record<string, string> = {
    Compute: '#FF9900',
    Storage: '#3F8624',
    Database: '#527FFF',
    Networking: '#8C4FFF',
    Messaging: '#E7157B',
    Security: '#DD344C',
    Monitoring: '#E7157B',
    DevOps: '#FF9900',
    Analytics: '#527FFF',
};

export const AWS_SERVICE_CATALOG: AwsServiceDef[] = [
    // ── Compute ─────────────────────────────────────────────────────
    {
        id: 'aws_ec2',
        name: 'EC2',
        category: 'Compute',
        description: 'Virtual servers in the cloud',
        defaultConfig: { instance_type: 't3.micro' },
    },
    {
        id: 'aws_lambda',
        name: 'Lambda',
        category: 'Compute',
        description: 'Serverless function execution',
        defaultConfig: { runtime: 'python3.12', memory: '128' },
    },
    {
        id: 'aws_ecs',
        name: 'ECS',
        category: 'Compute',
        description: 'Container orchestration service',
        defaultConfig: { launch_type: 'FARGATE' },
    },
    {
        id: 'aws_eks',
        name: 'EKS',
        category: 'Compute',
        description: 'Managed Kubernetes service',
        defaultConfig: { node_type: 't3.medium' },
    },

    // ── Storage ─────────────────────────────────────────────────────
    {
        id: 'aws_s3',
        name: 'S3',
        category: 'Storage',
        description: 'Object storage service',
        defaultConfig: { versioning: 'false' },
    },
    {
        id: 'aws_ebs',
        name: 'EBS',
        category: 'Storage',
        description: 'Block storage volumes',
        defaultConfig: { volume_type: 'gp3', size_gb: '20' },
    },

    // ── Database ────────────────────────────────────────────────────
    {
        id: 'aws_rds',
        name: 'RDS',
        category: 'Database',
        description: 'Managed relational database',
        defaultConfig: { engine: 'postgres', instance_type: 'db.t3.micro' },
    },
    {
        id: 'aws_dynamodb',
        name: 'DynamoDB',
        category: 'Database',
        description: 'NoSQL key-value database',
        defaultConfig: { billing_mode: 'PAY_PER_REQUEST' },
    },
    {
        id: 'aws_aurora',
        name: 'Aurora',
        category: 'Database',
        description: 'High-performance managed database',
        defaultConfig: { engine: 'aurora-postgresql' },
    },
    {
        id: 'aws_elasticache',
        name: 'ElastiCache',
        category: 'Database',
        description: 'In-memory caching (Redis/Memcached)',
        defaultConfig: { engine: 'redis', node_type: 'cache.t3.micro' },
    },

    // ── Networking ──────────────────────────────────────────────────
    {
        id: 'aws_vpc',
        name: 'VPC',
        category: 'Networking',
        description: 'Virtual private cloud network',
        defaultConfig: { cidr: '10.0.0.0/16' },
    },
    {
        id: 'aws_elb',
        name: 'Load Balancer',
        category: 'Networking',
        description: 'Application/Network load balancer',
        defaultConfig: { type: 'application' },
    },
    {
        id: 'aws_api_gateway',
        name: 'API Gateway',
        category: 'Networking',
        description: 'REST/WebSocket API management',
        defaultConfig: { type: 'REST' },
    },
    {
        id: 'aws_cloudfront',
        name: 'CloudFront',
        category: 'Networking',
        description: 'CDN for content delivery',
        defaultConfig: {},
    },
    {
        id: 'aws_route53',
        name: 'Route 53',
        category: 'Networking',
        description: 'DNS and domain management',
        defaultConfig: {},
    },
    {
        id: 'aws_transit_gateway',
        name: 'Transit Gateway',
        category: 'Networking',
        description: 'Connect VPCs and on-premises networks',
        defaultConfig: {},
    },
    {
        id: 'aws_nat_gateway',
        name: 'NAT Gateway',
        category: 'Networking',
        description: 'Enable outbound internet for private subnets',
        defaultConfig: {},
    },

    // ── Messaging ───────────────────────────────────────────────────
    {
        id: 'aws_sqs',
        name: 'SQS',
        category: 'Messaging',
        description: 'Message queue service',
        defaultConfig: { type: 'standard' },
    },
    {
        id: 'aws_sns',
        name: 'SNS',
        category: 'Messaging',
        description: 'Pub/sub notification service',
        defaultConfig: {},
    },
    {
        id: 'aws_eventbridge',
        name: 'EventBridge',
        category: 'Messaging',
        description: 'Serverless event bus',
        defaultConfig: {},
    },
    {
        id: 'aws_kinesis',
        name: 'Kinesis',
        category: 'Messaging',
        description: 'Real-time data streaming',
        defaultConfig: { shard_count: '1' },
    },

    // ── Security ────────────────────────────────────────────────────
    {
        id: 'aws_iam',
        name: 'IAM',
        category: 'Security',
        description: 'Identity and access management',
        defaultConfig: {},
    },
    {
        id: 'aws_cognito',
        name: 'Cognito',
        category: 'Security',
        description: 'User authentication and authorization',
        defaultConfig: {},
    },
    {
        id: 'aws_secrets_manager',
        name: 'Secrets Manager',
        category: 'Security',
        description: 'Manage secrets and credentials',
        defaultConfig: {},
    },

    // ── Monitoring ──────────────────────────────────────────────────
    {
        id: 'aws_cloudwatch',
        name: 'CloudWatch',
        category: 'Monitoring',
        description: 'Monitoring and observability',
        defaultConfig: {},
    },

    // ── DevOps ──────────────────────────────────────────────────────
    {
        id: 'aws_ecr',
        name: 'ECR',
        category: 'DevOps',
        description: 'Container image registry',
        defaultConfig: {},
    },

    // ── Analytics ───────────────────────────────────────────────────
    {
        id: 'aws_redshift',
        name: 'Redshift',
        category: 'Analytics',
        description: 'Data warehouse service',
        defaultConfig: { node_type: 'dc2.large' },
    },
];

/** Get services grouped by category */
export function getServicesByCategory(): Record<string, AwsServiceDef[]> {
    const grouped: Record<string, AwsServiceDef[]> = {};
    for (const svc of AWS_SERVICE_CATALOG) {
        if (!grouped[svc.category]) grouped[svc.category] = [];
        grouped[svc.category].push(svc);
    }
    return grouped;
}
