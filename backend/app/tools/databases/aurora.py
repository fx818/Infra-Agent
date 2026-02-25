"""Create Aurora, DynamoDB, Redshift, ElastiCache, Neptune, DocumentDB, Keyspaces, Timestream tools."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateAuroraClusterTool(BaseTool):
    name = "create_aurora_cluster"
    description = "Create an Amazon Aurora cluster (MySQL or PostgreSQL compatible) with high availability."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "cluster_id": {"type": "string"}, "label": {"type": "string"},
            "engine": {"type": "string", "description": "'aurora-mysql' or 'aurora-postgresql'.", "default": "aurora-postgresql"},
            "instance_class": {"type": "string", "default": "db.r5.large"},
            "instances": {"type": "integer", "description": "Number of instances.", "default": 2},
        },
        "required": ["cluster_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cluster_id"]
        engine = params.get("engine", "aurora-postgresql")
        inst_count = params.get("instances", 2)
        tf_code = f'''resource "aws_rds_cluster" "{cid}" {{
  cluster_identifier  = "${{var.project_name}}-{cid}"
  engine              = "{engine}"
  master_username     = "admin"
  master_password     = var.db_password
  skip_final_snapshot = true
  storage_encrypted   = true
  tags = {{ Name = "${{var.project_name}}-{cid}" }}
}}

resource "aws_rds_cluster_instance" "{cid}_instances" {{
  count              = {inst_count}
  identifier         = "${{var.project_name}}-{cid}-${{count.index}}"
  cluster_identifier = aws_rds_cluster.{cid}.id
  instance_class     = "{params.get('instance_class', 'db.r5.large')}"
  engine             = aws_rds_cluster.{cid}.engine
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_aurora", label=params.get("label", cid),
                          config=ToolNodeConfig(engine=engine, instance_type=params.get("instance_class", "db.r5.large"))),
            terraform_code={"database.tf": tf_code},
        )


class CreateDynamoDBTableTool(BaseTool):
    name = "create_dynamodb_table"
    description = "Create an Amazon DynamoDB table — fully managed NoSQL database with single-digit millisecond performance."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "table_id": {"type": "string"}, "label": {"type": "string"},
            "hash_key": {"type": "string", "default": "id"},
            "hash_key_type": {"type": "string", "description": "'S' (string), 'N' (number).", "default": "S"},
            "range_key": {"type": "string", "default": ""},
            "billing_mode": {"type": "string", "description": "'PAY_PER_REQUEST' or 'PROVISIONED'.", "default": "PAY_PER_REQUEST"},
        },
        "required": ["table_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["table_id"]
        hk = params.get("hash_key", "id")
        range_attr = ""
        if params.get("range_key"):
            range_attr = f'''
  range_key = "{params['range_key']}"
  attribute {{
    name = "{params['range_key']}"
    type = "S"
  }}'''
        tf_code = f'''resource "aws_dynamodb_table" "{tid}" {{
  name         = "${{var.project_name}}-{tid}"
  billing_mode = "{params.get('billing_mode', 'PAY_PER_REQUEST')}"
  hash_key     = "{hk}"
{range_attr}
  attribute {{
    name = "{hk}"
    type = "{params.get('hash_key_type', 'S')}"
  }}

  tags = {{ Name = "${{var.project_name}}-{tid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_dynamodb", label=params.get("label", tid),
                          config=ToolNodeConfig(extra={"hash_key": hk, "billing_mode": params.get("billing_mode", "PAY_PER_REQUEST")})),
            terraform_code={"database.tf": tf_code},
        )


class CreateRedshiftClusterTool(BaseTool):
    name = "create_redshift_cluster"
    description = "Create an Amazon Redshift data warehouse cluster for analytics and BI workloads."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "cluster_id": {"type": "string"}, "label": {"type": "string"},
            "node_type": {"type": "string", "default": "dc2.large"},
            "number_of_nodes": {"type": "integer", "default": 2},
            "db_name": {"type": "string", "default": "analytics"},
        },
        "required": ["cluster_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cluster_id"]
        tf_code = f'''resource "aws_redshift_cluster" "{cid}" {{
  cluster_identifier = "${{var.project_name}}-{cid}"
  database_name      = "{params.get('db_name', 'analytics')}"
  master_username    = "admin"
  master_password    = var.db_password
  node_type          = "{params.get('node_type', 'dc2.large')}"
  number_of_nodes    = {params.get('number_of_nodes', 2)}
  skip_final_snapshot = true
  tags = {{ Name = "${{var.project_name}}-{cid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_redshift", label=params.get("label", cid),
                          config=ToolNodeConfig(instance_type=params.get("node_type", "dc2.large"))),
            terraform_code={"database.tf": tf_code},
        )


class CreateElastiCacheClusterTool(BaseTool):
    name = "create_elasticache_cluster"
    description = "Create an Amazon ElastiCache cluster (Redis or Memcached) for in-memory caching."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "cache_id": {"type": "string"}, "label": {"type": "string"},
            "engine": {"type": "string", "description": "'redis' or 'memcached'.", "default": "redis"},
            "node_type": {"type": "string", "default": "cache.t3.micro"},
            "num_cache_nodes": {"type": "integer", "default": 1},
        },
        "required": ["cache_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cache_id"]
        engine = params.get("engine", "redis")
        tf_code = f'''resource "aws_elasticache_cluster" "{cid}" {{
  cluster_id      = "${{var.project_name}}-{cid}"
  engine          = "{engine}"
  node_type       = "{params.get('node_type', 'cache.t3.micro')}"
  num_cache_nodes = {params.get('num_cache_nodes', 1)}
  port            = {6379 if engine == 'redis' else 11211}
  tags = {{ Name = "${{var.project_name}}-{cid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_elasticache", label=params.get("label", cid),
                          config=ToolNodeConfig(engine=engine, instance_type=params.get("node_type", "cache.t3.micro"))),
            terraform_code={"database.tf": tf_code},
        )


class CreateNeptuneClusterTool(BaseTool):
    name = "create_neptune_cluster"
    description = "Create an Amazon Neptune graph database cluster for highly connected datasets."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "neptune_id": {"type": "string"}, "label": {"type": "string"},
            "instance_class": {"type": "string", "default": "db.r5.large"},
        },
        "required": ["neptune_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        nid = params["neptune_id"]
        tf_code = f'''resource "aws_neptune_cluster" "{nid}" {{
  cluster_identifier  = "${{var.project_name}}-{nid}"
  skip_final_snapshot = true
  tags = {{ Name = "${{var.project_name}}-{nid}" }}
}}

resource "aws_neptune_cluster_instance" "{nid}_instance" {{
  cluster_identifier = aws_neptune_cluster.{nid}.id
  instance_class     = "{params.get('instance_class', 'db.r5.large')}"
}}
'''
        return ToolResult(
            node=ToolNode(id=nid, type="aws_neptune", label=params.get("label", nid),
                          config=ToolNodeConfig(engine="neptune", instance_type=params.get("instance_class", "db.r5.large"))),
            terraform_code={"database.tf": tf_code},
        )


class CreateDocumentDBClusterTool(BaseTool):
    name = "create_documentdb_cluster"
    description = "Create an Amazon DocumentDB (MongoDB-compatible) cluster."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "docdb_id": {"type": "string"}, "label": {"type": "string"},
            "instance_class": {"type": "string", "default": "db.r5.large"},
            "instances": {"type": "integer", "default": 2},
        },
        "required": ["docdb_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        did = params["docdb_id"]
        tf_code = f'''resource "aws_docdb_cluster" "{did}" {{
  cluster_identifier  = "${{var.project_name}}-{did}"
  master_username     = "admin"
  master_password     = var.db_password
  skip_final_snapshot = true
  tags = {{ Name = "${{var.project_name}}-{did}" }}
}}

resource "aws_docdb_cluster_instance" "{did}_instances" {{
  count              = {params.get('instances', 2)}
  identifier         = "${{var.project_name}}-{did}-${{count.index}}"
  cluster_identifier = aws_docdb_cluster.{did}.id
  instance_class     = "{params.get('instance_class', 'db.r5.large')}"
}}
'''
        return ToolResult(
            node=ToolNode(id=did, type="aws_documentdb", label=params.get("label", did),
                          config=ToolNodeConfig(engine="documentdb", instance_type=params.get("instance_class", "db.r5.large"))),
            terraform_code={"database.tf": tf_code},
        )


class CreateKeyspacesTableTool(BaseTool):
    name = "create_keyspaces_table"
    description = "Create an Amazon Keyspaces (Apache Cassandra compatible) table."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "ks_id": {"type": "string"}, "label": {"type": "string"},
            "keyspace_name": {"type": "string", "default": "app_keyspace"},
            "table_name": {"type": "string", "default": "data"},
        },
        "required": ["ks_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        kid = params["ks_id"]
        tf_code = f'''resource "aws_keyspaces_keyspace" "{kid}_ks" {{
  name = "{params.get('keyspace_name', 'app_keyspace')}"
}}

resource "aws_keyspaces_table" "{kid}" {{
  keyspace_name = aws_keyspaces_keyspace.{kid}_ks.name
  table_name    = "{params.get('table_name', 'data')}"
  schema_definition {{
    column {{ name = "id" type = "text" }}
    partition_key {{ name = "id" }}
  }}
}}
'''
        return ToolResult(
            node=ToolNode(id=kid, type="aws_keyspaces", label=params.get("label", kid), config=ToolNodeConfig(engine="cassandra")),
            terraform_code={"database.tf": tf_code},
        )


class CreateTimestreamDatabaseTool(BaseTool):
    name = "create_timestream_database"
    description = "Create an Amazon Timestream time-series database for IoT and operational applications."
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "ts_id": {"type": "string"}, "label": {"type": "string"},
            "table_name": {"type": "string", "default": "metrics"},
            "retention_hours": {"type": "integer", "description": "Memory store retention in hours.", "default": 24},
            "retention_days": {"type": "integer", "description": "Magnetic store retention in days.", "default": 365},
        },
        "required": ["ts_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["ts_id"]
        tf_code = f'''resource "aws_timestreamwrite_database" "{tid}" {{
  database_name = "${{var.project_name}}-{tid}"
  tags = {{ Name = "${{var.project_name}}-{tid}" }}
}}

resource "aws_timestreamwrite_table" "{tid}_table" {{
  database_name = aws_timestreamwrite_database.{tid}.database_name
  table_name    = "{params.get('table_name', 'metrics')}"
  retention_properties {{
    memory_store_retention_period_in_hours  = {params.get('retention_hours', 24)}
    magnetic_store_retention_period_in_days = {params.get('retention_days', 365)}
  }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_timestream", label=params.get("label", tid), config=ToolNodeConfig(engine="timestream")),
            terraform_code={"database.tf": tf_code},
        )
