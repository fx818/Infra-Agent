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
    'AI/ML',
    'Application',
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
    'AI/ML': '#00A4A6',
    Application: '#C7131F',
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
    {
        id: 'aws_glue',
        name: 'Glue',
        category: 'Analytics',
        description: 'ETL and data catalog service',
        defaultConfig: {},
    },
    {
        id: 'aws_athena',
        name: 'Athena',
        category: 'Analytics',
        description: 'Serverless SQL queries on S3',
        defaultConfig: {},
    },
    {
        id: 'aws_emr',
        name: 'EMR',
        category: 'Analytics',
        description: 'Big data processing (Spark/Hadoop)',
        defaultConfig: { instance_type: 'm5.xlarge' },
    },
    {
        id: 'aws_opensearch',
        name: 'OpenSearch',
        category: 'Analytics',
        description: 'Search and analytics engine',
        defaultConfig: { instance_type: 't3.medium.search' },
    },
    {
        id: 'aws_msk',
        name: 'MSK (Kafka)',
        category: 'Analytics',
        description: 'Managed Apache Kafka service',
        defaultConfig: { instance_type: 'kafka.t3.small' },
    },

    // ── Additional Compute ──────────────────────────────────────────
    {
        id: 'aws_app_runner',
        name: 'App Runner',
        category: 'Compute',
        description: 'Deploy containerized web apps automatically',
        defaultConfig: { cpu: '1 vCPU', memory: '2 GB' },
    },
    {
        id: 'aws_step_functions',
        name: 'Step Functions',
        category: 'Compute',
        description: 'Serverless workflow orchestration',
        defaultConfig: { type: 'STANDARD' },
    },
    {
        id: 'aws_batch',
        name: 'Batch',
        category: 'Compute',
        description: 'Managed batch computing jobs',
        defaultConfig: { compute_type: 'MANAGED' },
    },
    {
        id: 'aws_elastic_beanstalk',
        name: 'Elastic Beanstalk',
        category: 'Compute',
        description: 'PaaS application deployment platform',
        defaultConfig: { platform: 'Python 3.12' },
    },
    {
        id: 'aws_lightsail',
        name: 'Lightsail',
        category: 'Compute',
        description: 'Simple VMs with predictable pricing',
        defaultConfig: { bundle_id: 'nano_3_0' },
    },

    // ── Additional Storage ──────────────────────────────────────────
    {
        id: 'aws_efs',
        name: 'EFS',
        category: 'Storage',
        description: 'Elastic shared file system (NFS)',
        defaultConfig: { throughput_mode: 'bursting' },
    },
    {
        id: 'aws_fsx',
        name: 'FSx',
        category: 'Storage',
        description: 'High-performance managed file systems',
        defaultConfig: { file_system_type: 'LUSTRE' },
    },
    {
        id: 'aws_glacier',
        name: 'S3 Glacier',
        category: 'Storage',
        description: 'Low-cost long-term archival storage',
        defaultConfig: { tier: 'BULK' },
    },

    // ── Additional Database ─────────────────────────────────────────
    {
        id: 'aws_neptune',
        name: 'Neptune',
        category: 'Database',
        description: 'Managed graph database',
        defaultConfig: { instance_type: 'db.t3.medium' },
    },
    {
        id: 'aws_documentdb',
        name: 'DocumentDB',
        category: 'Database',
        description: 'MongoDB-compatible document database',
        defaultConfig: { instance_type: 'db.t3.medium' },
    },
    {
        id: 'aws_timestream',
        name: 'Timestream',
        category: 'Database',
        description: 'Serverless time-series database',
        defaultConfig: {},
    },
    {
        id: 'aws_keyspaces',
        name: 'Keyspaces',
        category: 'Database',
        description: 'Managed Apache Cassandra service',
        defaultConfig: {},
    },

    // ── Additional Networking ───────────────────────────────────────
    {
        id: 'aws_security_group',
        name: 'Security Group',
        category: 'Networking',
        description: 'Virtual firewall for EC2/RDS/ECS',
        defaultConfig: {},
    },
    {
        id: 'aws_global_accelerator',
        name: 'Global Accelerator',
        category: 'Networking',
        description: 'Improve global application availability',
        defaultConfig: {},
    },
    {
        id: 'aws_vpn_gateway',
        name: 'VPN Gateway',
        category: 'Networking',
        description: 'Site-to-site VPN connectivity',
        defaultConfig: {},
    },
    {
        id: 'aws_apigatewayv2',
        name: 'API Gateway v2',
        category: 'Networking',
        description: 'HTTP/WebSocket API (v2)',
        defaultConfig: { protocol_type: 'HTTP' },
    },

    // ── Additional Security ─────────────────────────────────────────
    {
        id: 'aws_kms',
        name: 'KMS',
        category: 'Security',
        description: 'Key management and encryption',
        defaultConfig: {},
    },
    {
        id: 'aws_waf',
        name: 'WAF',
        category: 'Security',
        description: 'Web application firewall',
        defaultConfig: {},
    },
    {
        id: 'aws_guardduty',
        name: 'GuardDuty',
        category: 'Security',
        description: 'Intelligent threat detection service',
        defaultConfig: {},
    },
    {
        id: 'aws_acm',
        name: 'Certificate Manager',
        category: 'Security',
        description: 'SSL/TLS certificate provisioning',
        defaultConfig: {},
    },

    // ── Additional DevOps ───────────────────────────────────────────
    {
        id: 'aws_codepipeline',
        name: 'CodePipeline',
        category: 'DevOps',
        description: 'CI/CD pipeline automation',
        defaultConfig: {},
    },
    {
        id: 'aws_codebuild',
        name: 'CodeBuild',
        category: 'DevOps',
        description: 'Managed build service',
        defaultConfig: { compute_type: 'BUILD_GENERAL1_SMALL' },
    },
    {
        id: 'aws_cloudformation',
        name: 'CloudFormation',
        category: 'DevOps',
        description: 'Infrastructure as code stacks',
        defaultConfig: {},
    },
    {
        id: 'aws_amplify',
        name: 'Amplify',
        category: 'DevOps',
        description: 'Full-stack web/mobile app hosting',
        defaultConfig: {},
    },

    // ── AI/ML ────────────────────────────────────────────────────────
    {
        id: 'aws_sagemaker',
        name: 'SageMaker',
        category: 'AI/ML',
        description: 'Build, train and deploy ML models',
        defaultConfig: { instance_type: 'ml.t3.medium' },
    },
    {
        id: 'aws_bedrock',
        name: 'Bedrock',
        category: 'AI/ML',
        description: 'Foundation models as a managed service',
        defaultConfig: {},
    },
    {
        id: 'aws_rekognition',
        name: 'Rekognition',
        category: 'AI/ML',
        description: 'Image and video analysis with AI',
        defaultConfig: {},
    },
    {
        id: 'aws_comprehend',
        name: 'Comprehend',
        category: 'AI/ML',
        description: 'Natural language processing (NLP)',
        defaultConfig: {},
    },

    // ── Application ──────────────────────────────────────────────────
    {
        id: 'aws_appsync',
        name: 'AppSync',
        category: 'Application',
        description: 'Managed GraphQL API service',
        defaultConfig: {},
    },
    {
        id: 'aws_ses',
        name: 'SES',
        category: 'Application',
        description: 'Email sending and receiving service',
        defaultConfig: {},
    },
    {
        id: 'aws_pinpoint',
        name: 'Pinpoint',
        category: 'Application',
        description: 'Customer engagement and marketing',
        defaultConfig: {},
    },
    {
        id: 'aws_iot_core',
        name: 'IoT Core',
        category: 'Application',
        description: 'Connect and manage IoT devices',
        defaultConfig: {},
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
