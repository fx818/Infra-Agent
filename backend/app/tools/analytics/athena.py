"""Analytics & ML tools: Athena, Glue, EMR, SageMaker, QuickSight, LakeFormation, MSK, OpenSearch — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateAthenaWorkgroupTool(BaseTool):
    name = "create_athena_workgroup"
    description = "Create an Amazon Athena workgroup for serverless SQL querying of S3 data."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "athena_id": {"type": "string"}, "label": {"type": "string"},
            "output_bucket_ref": {"type": "string", "description": "S3 bucket for query results.", "default": ""},
        },
        "required": ["athena_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        aid = params["athena_id"]
        label = params.get("label", aid)
        configs = [{
            "service": "athena",
            "action": "create_work_group",
            "params": {
                "Name": f"__PROJECT__-{aid}",
                "Configuration": {"ResultConfiguration": {"OutputLocation": f"s3://__PROJECT__-{aid}-results/"}},
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{aid}"}],
            },
            "label": label,
            "resource_type": "aws_athena",
            "resource_id_path": None,
            "delete_action": "delete_work_group",
            "delete_params": {"WorkGroup": f"__PROJECT__-{aid}", "RecursiveDeleteOption": True},
        }]
        return ToolResult(
            node=ToolNode(id=aid, type="aws_athena", label=label, config=ToolNodeConfig()),
            boto3_config={"athena": configs},
        )


class CreateGlueJobTool(BaseTool):
    name = "create_glue_job"
    description = "Create an AWS Glue ETL job for data extraction, transformation, and loading."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "glue_id": {"type": "string"}, "label": {"type": "string"},
            "glue_version": {"type": "string", "default": "4.0"},
            "worker_type": {"type": "string", "default": "G.1X"},
            "num_workers": {"type": "integer", "default": 2},
        },
        "required": ["glue_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        gid = params["glue_id"]
        label = params.get("label", gid)
        configs = [
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{gid}-glue-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow", "Principal": {"Service": "glue.amazonaws.com"}}],
                    }),
                },
                "label": f"{label} — Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{gid}-glue-role"},
            },
            {
                "service": "glue",
                "action": "create_job",
                "params": {
                    "Name": f"__PROJECT__-{gid}",
                    "Role": f"__RESOLVE__:iam:create_role:{gid}-glue-role:Role.Arn",
                    "GlueVersion": params.get("glue_version", "4.0"),
                    "WorkerType": params.get("worker_type", "G.1X"),
                    "NumberOfWorkers": params.get("num_workers", 2),
                    "Command": {"Name": "glueetl", "ScriptLocation": f"s3://__PROJECT__-scripts/{gid}.py"},
                    "Tags": {"Name": f"__PROJECT__-{gid}"},
                },
                "label": label,
                "resource_type": "aws_glue_job",
                "resource_id_path": "Name",
                "delete_action": "delete_job",
                "delete_params": {"JobName": f"__PROJECT__-{gid}"},
            },
        ]
        return ToolResult(
            node=ToolNode(id=gid, type="aws_glue", label=label, config=ToolNodeConfig()),
            boto3_config={"glue": configs},
        )


class CreateEMRClusterTool(BaseTool):
    name = "create_emr_cluster"
    description = "Create an Amazon EMR cluster for big data processing with Spark, Hadoop, etc."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "emr_id": {"type": "string"}, "label": {"type": "string"},
            "release_label": {"type": "string", "default": "emr-7.0.0"},
            "instance_type": {"type": "string", "default": "m5.xlarge"},
            "instance_count": {"type": "integer", "default": 3},
            "applications": {"type": "array", "items": {"type": "string"}, "default": ["Spark"]},
        },
        "required": ["emr_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        eid = params["emr_id"]
        label = params.get("label", eid)
        inst_type = params.get("instance_type", "m5.xlarge")
        inst_count = params.get("instance_count", 3)
        apps = [{"Name": a} for a in params.get("applications", ["Spark"])]

        configs = [
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{eid}-emr-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow", "Principal": {"Service": "elasticmapreduce.amazonaws.com"}}],
                    }),
                },
                "label": f"{label} — EMR Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{eid}-emr-role"},
            },
            {
                "service": "emr",
                "action": "run_job_flow",
                "params": {
                    "Name": f"__PROJECT__-{eid}",
                    "ReleaseLabel": params.get("release_label", "emr-7.0.0"),
                    "Applications": apps,
                    "ServiceRole": f"__PROJECT__-{eid}-emr-role",
                    "JobFlowRole": f"__PROJECT__-{eid}-ec2-role",
                    "Instances": {
                        "MasterInstanceType": inst_type,
                        "SlaveInstanceType": inst_type,
                        "InstanceCount": inst_count,
                        "KeepJobFlowAliveWhenNoSteps": True,
                    },
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{eid}"}],
                },
                "label": label,
                "resource_type": "aws_emr",
                "resource_id_path": "JobFlowId",
                "delete_action": "terminate_job_flows",
                "delete_params_key": "JobFlowIds",
            },
        ]
        return ToolResult(
            node=ToolNode(id=eid, type="aws_emr", label=label,
                          config=ToolNodeConfig(instance_type=inst_type)),
            boto3_config={"emr": configs},
        )


class CreateSageMakerEndpointTool(BaseTool):
    name = "create_sagemaker_endpoint"
    description = "Create an Amazon SageMaker endpoint for ML model inference."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "sm_id": {"type": "string"}, "label": {"type": "string"},
            "instance_type": {"type": "string", "default": "ml.m5.large"},
            "instance_count": {"type": "integer", "default": 1},
        },
        "required": ["sm_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["sm_id"]
        label = params.get("label", sid)
        configs = [
            {
                "service": "sagemaker",
                "action": "create_endpoint_config",
                "params": {
                    "EndpointConfigName": f"__PROJECT__-{sid}",
                    "ProductionVariants": [{
                        "VariantName": "primary",
                        "InitialInstanceCount": params.get("instance_count", 1),
                        "InstanceType": params.get("instance_type", "ml.m5.large"),
                    }],
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}],
                },
                "label": f"{label} — Config",
                "resource_type": "aws_sagemaker_endpoint_config",
                "resource_id_path": "EndpointConfigArn",
                "delete_action": "delete_endpoint_config",
                "delete_params": {"EndpointConfigName": f"__PROJECT__-{sid}"},
            },
            {
                "service": "sagemaker",
                "action": "create_endpoint",
                "params": {
                    "EndpointName": f"__PROJECT__-{sid}",
                    "EndpointConfigName": f"__PROJECT__-{sid}",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}],
                },
                "label": label,
                "resource_type": "aws_sagemaker_endpoint",
                "resource_id_path": "EndpointArn",
                "delete_action": "delete_endpoint",
                "delete_params": {"EndpointName": f"__PROJECT__-{sid}"},
            },
        ]
        return ToolResult(
            node=ToolNode(id=sid, type="aws_sagemaker", label=label,
                          config=ToolNodeConfig(instance_type=params.get("instance_type", "ml.m5.large"))),
            boto3_config={"sagemaker": configs},
        )


class CreateQuickSightDatasetTool(BaseTool):
    name = "create_quicksight_dataset"
    description = "Create an Amazon QuickSight dataset for BI visualizations."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {"qs_id": {"type": "string"}, "label": {"type": "string"}},
        "required": ["qs_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        qid = params["qs_id"]
        label = params.get("label", qid)
        # QuickSight requires console setup — this is a placeholder
        configs = [{
            "service": "quicksight",
            "action": "list_data_sets",
            "params": {"AwsAccountId": "__ACCOUNT_ID__"},
            "label": label,
            "resource_type": "aws_quicksight",
            "is_lookup": True,
        }]
        return ToolResult(
            node=ToolNode(id=qid, type="aws_quicksight", label=label, config=ToolNodeConfig()),
            boto3_config={"quicksight": configs},
        )


class CreateLakeFormationResourceTool(BaseTool):
    name = "create_lake_formation_resource"
    description = "Register an S3 location with AWS Lake Formation for data lake governance."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "lf_id": {"type": "string"}, "label": {"type": "string"},
            "s3_bucket_ref": {"type": "string", "description": "S3 bucket resource ID."},
        },
        "required": ["lf_id", "label", "s3_bucket_ref"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        lid = params["lf_id"]
        label = params.get("label", lid)
        configs = [{
            "service": "lakeformation",
            "action": "register_resource",
            "params": {"ResourceArn": f"arn:aws:s3:::__PROJECT__-{params['s3_bucket_ref']}"},
            "label": label,
            "resource_type": "aws_lake_formation",
            "resource_id_path": None,
            "delete_action": "deregister_resource",
            "delete_params": {"ResourceArn": f"arn:aws:s3:::__PROJECT__-{params['s3_bucket_ref']}"},
        }]
        return ToolResult(
            node=ToolNode(id=lid, type="aws_lake_formation", label=label, config=ToolNodeConfig()),
            boto3_config={"lakeformation": configs},
            edges=[{"from": lid, "to": params["s3_bucket_ref"], "label": "governs"}],
        )


class CreateMSKClusterTool(BaseTool):
    name = "create_msk_cluster"
    description = "Create an Amazon MSK (Managed Streaming for Apache Kafka) cluster."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "msk_id": {"type": "string"}, "label": {"type": "string"},
            "kafka_version": {"type": "string", "default": "3.6.0"},
            "broker_instance_type": {"type": "string", "default": "kafka.m5.large"},
            "number_of_broker_nodes": {"type": "integer", "default": 3},
        },
        "required": ["msk_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        mid = params["msk_id"]
        label = params.get("label", mid)
        configs = [{
            "service": "kafka",
            "action": "create_cluster",
            "params": {
                "ClusterName": f"__PROJECT__-{mid}",
                "KafkaVersion": params.get("kafka_version", "3.6.0"),
                "NumberOfBrokerNodes": params.get("number_of_broker_nodes", 3),
                "BrokerNodeGroupInfo": {
                    "InstanceType": params.get("broker_instance_type", "kafka.m5.large"),
                    "ClientSubnets": "__DEFAULT_SUBNETS__",
                    "StorageInfo": {"EbsStorageInfo": {"VolumeSize": 100}},
                },
                "Tags": {"Name": f"__PROJECT__-{mid}"},
            },
            "label": label,
            "resource_type": "aws_msk",
            "resource_id_path": "ClusterArn",
            "delete_action": "delete_cluster",
            "delete_params_key": "ClusterArn",
        }]
        return ToolResult(
            node=ToolNode(id=mid, type="aws_msk", label=label,
                          config=ToolNodeConfig(instance_type=params.get("broker_instance_type", "kafka.m5.large"))),
            boto3_config={"kafka": configs},
        )


class CreateOpenSearchDomainTool(BaseTool):
    name = "create_opensearch_domain"
    description = "Create an Amazon OpenSearch Service domain for search and log analytics."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "os_id": {"type": "string"}, "label": {"type": "string"},
            "engine_version": {"type": "string", "default": "OpenSearch_2.11"},
            "instance_type": {"type": "string", "default": "t3.small.search"},
            "instance_count": {"type": "integer", "default": 2},
        },
        "required": ["os_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        oid = params["os_id"]
        label = params.get("label", oid)
        configs = [{
            "service": "opensearch",
            "action": "create_domain",
            "params": {
                "DomainName": f"__PROJECT__-{oid}",
                "EngineVersion": params.get("engine_version", "OpenSearch_2.11"),
                "ClusterConfig": {
                    "InstanceType": params.get("instance_type", "t3.small.search"),
                    "InstanceCount": params.get("instance_count", 2),
                },
                "EBSOptions": {"EBSEnabled": True, "VolumeSize": 20, "VolumeType": "gp3"},
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{oid}"}],
            },
            "label": label,
            "resource_type": "aws_opensearch",
            "resource_id_path": "DomainStatus.ARN",
            "delete_action": "delete_domain",
            "delete_params": {"DomainName": f"__PROJECT__-{oid}"},
        }]
        return ToolResult(
            node=ToolNode(id=oid, type="aws_opensearch", label=label,
                          config=ToolNodeConfig(instance_type=params.get("instance_type", "t3.small.search"))),
            boto3_config={"opensearch": configs},
        )
