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
    ['aws_ecr', 'aws_app_runner'],
    ['aws_codepipeline', 'aws_codebuild'],
    ['aws_codebuild', 'aws_ecr'],
    ['aws_codepipeline', 'aws_ecs'],
    ['aws_codepipeline', 'aws_lambda'],
    ['aws_cloudformation', 'aws_ec2'],
    ['aws_cloudformation', 'aws_lambda'],
    ['aws_amplify', 'aws_appsync'],
    ['aws_amplify', 'aws_cognito'],

    // Additional Compute
    ['aws_app_runner', 'aws_rds'],
    ['aws_app_runner', 'aws_dynamodb'],
    ['aws_app_runner', 'aws_elasticache'],
    ['aws_app_runner', 'aws_s3'],
    ['aws_step_functions', 'aws_lambda'],
    ['aws_step_functions', 'aws_ecs'],
    ['aws_step_functions', 'aws_sqs'],
    ['aws_step_functions', 'aws_dynamodb'],
    ['aws_step_functions', 'aws_sns'],
    ['aws_eventbridge', 'aws_step_functions'],
    ['aws_batch', 'aws_s3'],
    ['aws_batch', 'aws_efs'],
    ['aws_elastic_beanstalk', 'aws_rds'],
    ['aws_elastic_beanstalk', 'aws_elasticache'],
    ['aws_elastic_beanstalk', 'aws_s3'],

    // Additional Storage
    ['aws_ec2', 'aws_efs'],
    ['aws_ecs', 'aws_efs'],
    ['aws_lambda', 'aws_efs'],
    ['aws_eks', 'aws_efs'],
    ['aws_s3', 'aws_glacier'],

    // Additional Database
    ['aws_lambda', 'aws_neptune'],
    ['aws_ec2', 'aws_neptune'],
    ['aws_ecs', 'aws_neptune'],
    ['aws_lambda', 'aws_documentdb'],
    ['aws_ec2', 'aws_documentdb'],
    ['aws_ecs', 'aws_documentdb'],
    ['aws_lambda', 'aws_timestream'],
    ['aws_ec2', 'aws_timestream'],
    ['aws_lambda', 'aws_keyspaces'],
    ['aws_ec2', 'aws_keyspaces'],

    // Additional Networking
    ['aws_vpc', 'aws_security_group'],
    ['aws_security_group', 'aws_ec2'],
    ['aws_security_group', 'aws_rds'],
    ['aws_security_group', 'aws_ecs'],
    ['aws_security_group', 'aws_lambda'],
    ['aws_global_accelerator', 'aws_elb'],
    ['aws_global_accelerator', 'aws_ec2'],
    ['aws_global_accelerator', 'aws_api_gateway'],
    ['aws_vpn_gateway', 'aws_vpc'],
    ['aws_route53', 'aws_global_accelerator'],
    ['aws_apigatewayv2', 'aws_lambda'],
    ['aws_apigatewayv2', 'aws_ecs'],
    ['aws_apigatewayv2', 'aws_ec2'],
    ['aws_cloudfront', 'aws_apigatewayv2'],
    ['aws_route53', 'aws_apigatewayv2'],
    ['aws_cognito', 'aws_apigatewayv2'],

    // Additional Security
    ['aws_kms', 'aws_s3'],
    ['aws_kms', 'aws_rds'],
    ['aws_kms', 'aws_dynamodb'],
    ['aws_kms', 'aws_lambda'],
    ['aws_kms', 'aws_ebs'],
    ['aws_waf', 'aws_cloudfront'],
    ['aws_waf', 'aws_api_gateway'],
    ['aws_waf', 'aws_apigatewayv2'],
    ['aws_waf', 'aws_elb'],
    ['aws_acm', 'aws_cloudfront'],
    ['aws_acm', 'aws_elb'],
    ['aws_acm', 'aws_api_gateway'],
    ['aws_guardduty', 'aws_cloudwatch'],
    ['aws_guardduty', 'aws_sns'],

    // Analytics
    ['aws_kinesis', 'aws_s3'],
    ['aws_kinesis', 'aws_redshift'],
    ['aws_kinesis', 'aws_opensearch'],
    ['aws_s3', 'aws_glue'],
    ['aws_glue', 'aws_s3'],
    ['aws_glue', 'aws_redshift'],
    ['aws_glue', 'aws_athena'],
    ['aws_s3', 'aws_athena'],
    ['aws_athena', 'aws_s3'],
    ['aws_emr', 'aws_s3'],
    ['aws_emr', 'aws_hdfs'],
    ['aws_msk', 'aws_lambda'],
    ['aws_msk', 'aws_glue'],
    ['aws_msk', 'aws_s3'],
    ['aws_msk', 'aws_opensearch'],
    ['aws_opensearch', 'aws_lambda'],
    ['aws_lambda', 'aws_opensearch'],
    ['aws_kinesis', 'aws_glue'],
    ['aws_redshift', 'aws_s3'],

    // AI/ML
    ['aws_sagemaker', 'aws_s3'],
    ['aws_lambda', 'aws_sagemaker'],
    ['aws_lambda', 'aws_bedrock'],
    ['aws_lambda', 'aws_rekognition'],
    ['aws_lambda', 'aws_comprehend'],
    ['aws_ec2', 'aws_sagemaker'],
    ['aws_api_gateway', 'aws_sagemaker'],
    ['aws_apigatewayv2', 'aws_sagemaker'],
    ['aws_s3', 'aws_rekognition'],
    ['aws_s3', 'aws_comprehend'],

    // Application
    ['aws_appsync', 'aws_dynamodb'],
    ['aws_appsync', 'aws_lambda'],
    ['aws_appsync', 'aws_rds'],
    ['aws_lambda', 'aws_ses'],
    ['aws_ec2', 'aws_ses'],
    ['aws_lambda', 'aws_pinpoint'],
    ['aws_lambda', 'aws_iot_core'],
    ['aws_iot_core', 'aws_lambda'],
    ['aws_iot_core', 'aws_kinesis'],
    ['aws_iot_core', 'aws_sqs'],
    ['aws_iot_core', 'aws_dynamodb'],
    ['aws_cognito', 'aws_appsync'],
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
        'aws_apigatewayv2::aws_lambda': 'triggers',
        'aws_cloudfront::aws_s3': 'origin',
        'aws_cloudfront::aws_elb': 'origin',
        'aws_route53::aws_cloudfront': 'resolves to',
        'aws_route53::aws_elb': 'resolves to',
        'aws_sqs::aws_lambda': 'triggers',
        'aws_sns::aws_lambda': 'triggers',
        'aws_sns::aws_sqs': 'delivers to',
        'aws_eventbridge::aws_lambda': 'triggers',
        'aws_eventbridge::aws_step_functions': 'triggers',
        'aws_eventbridge::aws_sqs': 'delivers to',
        'aws_vpc::aws_ec2': 'contains',
        'aws_vpc::aws_rds': 'contains',
        'aws_vpc::aws_ecs': 'contains',
        'aws_cognito::aws_api_gateway': 'authorizes',
        'aws_cognito::aws_apigatewayv2': 'authorizes',
        'aws_cognito::aws_appsync': 'authorizes',
        'aws_ecr::aws_ecs': 'provides image',
        'aws_ecr::aws_eks': 'provides image',
        'aws_ecr::aws_app_runner': 'provides image',
        'aws_codepipeline::aws_codebuild': 'triggers',
        'aws_codebuild::aws_ecr': 'pushes to',
        'aws_waf::aws_cloudfront': 'protects',
        'aws_waf::aws_api_gateway': 'protects',
        'aws_acm::aws_cloudfront': 'provides TLS',
        'aws_acm::aws_elb': 'provides TLS',
        'aws_kms::aws_s3': 'encrypts',
        'aws_kms::aws_rds': 'encrypts',
        'aws_kms::aws_dynamodb': 'encrypts',
        'aws_step_functions::aws_lambda': 'invokes',
        'aws_step_functions::aws_ecs': 'runs task',
        'aws_step_functions::aws_dynamodb': 'reads/writes',
        'aws_appsync::aws_dynamodb': 'reads/writes',
        'aws_appsync::aws_lambda': 'invokes',
        'aws_lambda::aws_bedrock': 'invokes',
        'aws_lambda::aws_sagemaker': 'invokes',
        'aws_sagemaker::aws_s3': 'reads/writes',
        'aws_glue::aws_s3': 'reads/writes',
        'aws_glue::aws_redshift': 'loads to',
        'aws_athena::aws_s3': 'queries',
        'aws_msk::aws_lambda': 'triggers',
        'aws_iot_core::aws_lambda': 'triggers',
        'aws_iot_core::aws_kinesis': 'streams to',
        'aws_global_accelerator::aws_elb': 'routes to',
        'aws_lambda::aws_ses': 'sends email via',
        'aws_lambda::aws_opensearch': 'indexes to',
        'aws_guardduty::aws_sns': 'alerts via',
    };
    return labels[`${sourceType}::${targetType}`] || 'connects to';
}
