/**
 * AWS service connection rules for the drag-build canvas.
 * Defines which services can be connected to which.
 */

// Set of allowed [source, target] pairs.
// Each pair means: source service CAN connect to target service.
const RAW_PAIRS: [string, string][] = [
    // Compute → Database
    ['aws_ec2', 'aws_rds'],
    ['aws_ec2', 'aws_dynamodb'],
    ['aws_ec2', 'aws_aurora'],
    ['aws_ec2', 'aws_elasticache'],
    ['aws_lambda', 'aws_rds'],
    ['aws_lambda', 'aws_dynamodb'],
    ['aws_lambda', 'aws_aurora'],
    ['aws_lambda', 'aws_elasticache'],
    ['aws_ecs', 'aws_rds'],
    ['aws_ecs', 'aws_dynamodb'],
    ['aws_ecs', 'aws_aurora'],
    ['aws_ecs', 'aws_elasticache'],
    ['aws_eks', 'aws_rds'],
    ['aws_eks', 'aws_dynamodb'],

    // Compute → Storage
    ['aws_ec2', 'aws_s3'],
    ['aws_ec2', 'aws_ebs'],
    ['aws_lambda', 'aws_s3'],
    ['aws_ecs', 'aws_s3'],
    ['aws_eks', 'aws_s3'],

    // Networking → Compute
    ['aws_elb', 'aws_ec2'],
    ['aws_elb', 'aws_ecs'],
    ['aws_elb', 'aws_eks'],
    ['aws_api_gateway', 'aws_lambda'],
    ['aws_api_gateway', 'aws_ecs'],
    ['aws_api_gateway', 'aws_ec2'],
    ['aws_cloudfront', 'aws_s3'],
    ['aws_cloudfront', 'aws_elb'],
    ['aws_cloudfront', 'aws_api_gateway'],
    ['aws_route53', 'aws_cloudfront'],
    ['aws_route53', 'aws_elb'],
    ['aws_route53', 'aws_api_gateway'],
    ['aws_route53', 'aws_ec2'],

    // VPC contains everything
    ['aws_vpc', 'aws_ec2'],
    ['aws_vpc', 'aws_ecs'],
    ['aws_vpc', 'aws_eks'],
    ['aws_vpc', 'aws_rds'],
    ['aws_vpc', 'aws_elasticache'],
    ['aws_vpc', 'aws_elb'],
    ['aws_vpc', 'aws_nat_gateway'],
    ['aws_vpc', 'aws_transit_gateway'],

    // NAT/Transit
    ['aws_nat_gateway', 'aws_ec2'],
    ['aws_nat_gateway', 'aws_ecs'],
    ['aws_transit_gateway', 'aws_vpc'],

    // Messaging
    ['aws_lambda', 'aws_sqs'],
    ['aws_lambda', 'aws_sns'],
    ['aws_lambda', 'aws_eventbridge'],
    ['aws_lambda', 'aws_kinesis'],
    ['aws_ec2', 'aws_sqs'],
    ['aws_ec2', 'aws_sns'],
    ['aws_ecs', 'aws_sqs'],
    ['aws_ecs', 'aws_sns'],
    ['aws_sqs', 'aws_lambda'],
    ['aws_sns', 'aws_lambda'],
    ['aws_sns', 'aws_sqs'],
    ['aws_eventbridge', 'aws_lambda'],
    ['aws_eventbridge', 'aws_sqs'],
    ['aws_eventbridge', 'aws_sns'],
    ['aws_kinesis', 'aws_lambda'],

    // Security
    ['aws_cognito', 'aws_api_gateway'],
    ['aws_iam', 'aws_ec2'],
    ['aws_iam', 'aws_lambda'],
    ['aws_iam', 'aws_ecs'],
    ['aws_secrets_manager', 'aws_lambda'],
    ['aws_secrets_manager', 'aws_ec2'],
    ['aws_secrets_manager', 'aws_ecs'],

    // Monitoring
    ['aws_cloudwatch', 'aws_ec2'],
    ['aws_cloudwatch', 'aws_lambda'],
    ['aws_cloudwatch', 'aws_ecs'],
    ['aws_cloudwatch', 'aws_rds'],
    ['aws_cloudwatch', 'aws_sns'],

    // DevOps
    ['aws_ecr', 'aws_ecs'],
    ['aws_ecr', 'aws_eks'],
];

// Build a Set for O(1) lookup
const allowedSet = new Set(RAW_PAIRS.map(([s, t]) => `${s}::${t}`));

/**
 * Check if a connection from sourceType to targetType is allowed.
 * Returns true if the connection is valid per AWS dependency graph.
 */
export function isConnectionAllowed(sourceType: string, targetType: string): boolean {
    return allowedSet.has(`${sourceType}::${targetType}`);
}

/**
 * Get all services that a given service type can connect TO.
 */
export function getAllowedTargets(sourceType: string): string[] {
    return RAW_PAIRS
        .filter(([s]) => s === sourceType)
        .map(([, t]) => t);
}

/**
 * Get the label for a connection between two service types.
 */
export function getConnectionLabel(sourceType: string, targetType: string): string {
    const labels: Record<string, string> = {
        'aws_elb::aws_ec2': 'routes to',
        'aws_elb::aws_ecs': 'routes to',
        'aws_api_gateway::aws_lambda': 'triggers',
        'aws_cloudfront::aws_s3': 'origin',
        'aws_cloudfront::aws_elb': 'origin',
        'aws_route53::aws_cloudfront': 'resolves to',
        'aws_route53::aws_elb': 'resolves to',
        'aws_sqs::aws_lambda': 'triggers',
        'aws_sns::aws_lambda': 'triggers',
        'aws_sns::aws_sqs': 'delivers to',
        'aws_eventbridge::aws_lambda': 'triggers',
        'aws_vpc::aws_ec2': 'contains',
        'aws_vpc::aws_rds': 'contains',
        'aws_vpc::aws_ecs': 'contains',
        'aws_cognito::aws_api_gateway': 'authorizes',
    };
    return labels[`${sourceType}::${targetType}`] || 'connects to';
}
