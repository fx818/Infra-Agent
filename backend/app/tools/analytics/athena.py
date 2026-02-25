"""Analytics & ML tools: Athena, Glue, EMR, SageMaker, QuickSight, LakeFormation, MSK, OpenSearch."""
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
        tf_code = f'''resource "aws_athena_workgroup" "{aid}" {{
  name = "${{var.project_name}}-{aid}"
  configuration {{
    result_configuration {{
      output_location = "s3://${{var.project_name}}-{aid}-results/"
    }}
  }}
  tags = {{ Name = "${{var.project_name}}-{aid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=aid, type="aws_athena", label=params.get("label", aid), config=ToolNodeConfig()),
            terraform_code={"analytics.tf": tf_code},
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
        tf_code = f'''resource "aws_glue_job" "{gid}" {{
  name     = "${{var.project_name}}-{gid}"
  role_arn = aws_iam_role.{gid}_glue_role.arn
  glue_version = "{params.get('glue_version', '4.0')}"
  worker_type  = "{params.get('worker_type', 'G.1X')}"
  number_of_workers = {params.get('num_workers', 2)}
  command {{
    script_location = "s3://${{var.project_name}}-scripts/{gid}.py"
  }}
  tags = {{ Name = "${{var.project_name}}-{gid}" }}
}}

resource "aws_iam_role" "{gid}_glue_role" {{
  name = "${{var.project_name}}-{gid}-glue-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "glue.amazonaws.com" }} }}]
  }})
}}
'''
        return ToolResult(
            node=ToolNode(id=gid, type="aws_glue", label=params.get("label", gid), config=ToolNodeConfig()),
            terraform_code={"analytics.tf": tf_code},
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
        apps = "\n".join(f'  application {{ name = "{a}" }}' for a in params.get("applications", ["Spark"]))
        tf_code = f'''resource "aws_emr_cluster" "{eid}" {{
  name          = "${{var.project_name}}-{eid}"
  release_label = "{params.get('release_label', 'emr-7.0.0')}"
  service_role  = aws_iam_role.{eid}_emr_role.arn
{apps}

  ec2_attributes {{
    instance_profile = aws_iam_instance_profile.{eid}_profile.arn
  }}

  master_instance_group {{
    instance_type  = "{params.get('instance_type', 'm5.xlarge')}"
    instance_count = 1
  }}

  core_instance_group {{
    instance_type  = "{params.get('instance_type', 'm5.xlarge')}"
    instance_count = {params.get('instance_count', 3) - 1}
  }}

  tags = {{ Name = "${{var.project_name}}-{eid}" }}
}}

resource "aws_iam_role" "{eid}_emr_role" {{
  name = "${{var.project_name}}-{eid}-emr-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "elasticmapreduce.amazonaws.com" }} }}]
  }})
}}

resource "aws_iam_instance_profile" "{eid}_profile" {{
  name = "${{var.project_name}}-{eid}-profile"
  role = aws_iam_role.{eid}_ec2_role.name
}}

resource "aws_iam_role" "{eid}_ec2_role" {{
  name = "${{var.project_name}}-{eid}-ec2-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "ec2.amazonaws.com" }} }}]
  }})
}}
'''
        return ToolResult(
            node=ToolNode(id=eid, type="aws_emr", label=params.get("label", eid),
                          config=ToolNodeConfig(instance_type=params.get("instance_type", "m5.xlarge"))),
            terraform_code={"analytics.tf": tf_code},
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
        tf_code = f'''resource "aws_sagemaker_endpoint_configuration" "{sid}_config" {{
  name = "${{var.project_name}}-{sid}"
  production_variants {{
    variant_name           = "primary"
    initial_instance_count = {params.get('instance_count', 1)}
    instance_type          = "{params.get('instance_type', 'ml.m5.large')}"
  }}
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}

resource "aws_sagemaker_endpoint" "{sid}" {{
  name                 = "${{var.project_name}}-{sid}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.{sid}_config.name
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_sagemaker", label=params.get("label", sid),
                          config=ToolNodeConfig(instance_type=params.get("instance_type", "ml.m5.large"))),
            terraform_code={"analytics.tf": tf_code},
        )


class CreateQuickSightDatasetTool(BaseTool):
    name = "create_quicksight_dataset"
    description = "Create an Amazon QuickSight dataset for business intelligence visualizations."
    category = "analytics"
    parameters = {
        "type": "object",
        "properties": {
            "qs_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["qs_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        qid = params["qs_id"]
        tf_code = f'''# QuickSight datasets typically require manual configuration via console.
# This creates the initial data source reference.
resource "aws_quicksight_data_source" "{qid}" {{
  data_source_id = "${{var.project_name}}-{qid}"
  name           = "${{var.project_name}}-{qid}"
  type           = "S3"
  parameters {{
    s3 {{
      manifest_file_location {{
        bucket = "${{var.project_name}}-data"
        key    = "manifest.json"
      }}
    }}
  }}
}}
'''
        return ToolResult(
            node=ToolNode(id=qid, type="aws_quicksight", label=params.get("label", qid), config=ToolNodeConfig()),
            terraform_code={"analytics.tf": tf_code},
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
        tf_code = f'''resource "aws_lakeformation_resource" "{lid}" {{
  arn = aws_s3_bucket.{params['s3_bucket_ref']}.arn
}}
'''
        return ToolResult(
            node=ToolNode(id=lid, type="aws_lake_formation", label=params.get("label", lid), config=ToolNodeConfig()),
            terraform_code={"analytics.tf": tf_code},
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
        tf_code = f'''resource "aws_msk_cluster" "{mid}" {{
  cluster_name           = "${{var.project_name}}-{mid}"
  kafka_version          = "{params.get('kafka_version', '3.6.0')}"
  number_of_broker_nodes = {params.get('number_of_broker_nodes', 3)}

  broker_node_group_info {{
    instance_type = "{params.get('broker_instance_type', 'kafka.m5.large')}"
    client_subnets = [for s in aws_subnet.private : s.id]
    storage_info {{
      ebs_storage_info {{ volume_size = 100 }}
    }}
  }}
  tags = {{ Name = "${{var.project_name}}-{mid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=mid, type="aws_msk", label=params.get("label", mid),
                          config=ToolNodeConfig(instance_type=params.get("broker_instance_type", "kafka.m5.large"))),
            terraform_code={"analytics.tf": tf_code},
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
        tf_code = f'''resource "aws_opensearch_domain" "{oid}" {{
  domain_name    = "${{var.project_name}}-{oid}"
  engine_version = "{params.get('engine_version', 'OpenSearch_2.11')}"

  cluster_config {{
    instance_type  = "{params.get('instance_type', 't3.small.search')}"
    instance_count = {params.get('instance_count', 2)}
  }}

  ebs_options {{
    ebs_enabled = true
    volume_size = 20
  }}

  tags = {{ Name = "${{var.project_name}}-{oid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=oid, type="aws_opensearch", label=params.get("label", oid),
                          config=ToolNodeConfig(instance_type=params.get("instance_type", "t3.small.search"))),
            terraform_code={"analytics.tf": tf_code},
        )
