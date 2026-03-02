"""Database tools: Aurora, DynamoDB, Redshift, ElastiCache, Neptune, DocumentDB, Keyspaces, Timestream — provisions via boto3."""
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
        label = params.get("label", cid)
        raw_engine = params.get("engine", "aurora-postgresql")
        inst_class = params.get("instance_class", "db.r5.large")
        inst_count = params.get("instances", 2)

        engine_map = {"postgres": "aurora-postgresql", "postgresql": "aurora-postgresql", "mysql": "aurora-mysql"}
        engine = engine_map.get(raw_engine.lower(), raw_engine)
        if engine not in ("aurora-mysql", "aurora-postgresql"):
            engine = "aurora-postgresql"

        safe_cid = cid.lower().replace("_", "-")

        configs = [
            {
                "service": "rds",
                "action": "create_db_cluster",
                "params": {
                    "DBClusterIdentifier": f"__PROJECT__-{safe_cid}",
                    "Engine": engine,
                    "MasterUsername": "dbadmin",
                    "MasterUserPassword": "ChangeMe123!",
                    "StorageEncrypted": True,
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{safe_cid}"}],
                },
                "label": f"{label} — Cluster",
                "resource_type": "aws_aurora_cluster",
                "resource_id_path": "DBCluster.DBClusterIdentifier",
                "delete_action": "delete_db_cluster",
                "delete_params": {"DBClusterIdentifier": f"__PROJECT__-{safe_cid}", "SkipFinalSnapshot": True},
                "waiter": "db_cluster_available",
                "waiter_params": {"DBClusterIdentifier": f"__PROJECT__-{safe_cid}"},
            },
        ]

        for i in range(inst_count):
            configs.append({
                "service": "rds",
                "action": "create_db_instance",
                "params": {
                    "DBInstanceIdentifier": f"__PROJECT__-{safe_cid}-{i}",
                    "DBClusterIdentifier": f"__PROJECT__-{safe_cid}",
                    "DBInstanceClass": inst_class,
                    "Engine": engine,
                },
                "label": f"{label} — Instance {i}",
                "resource_type": "aws_aurora_instance",
                "resource_id_path": "DBInstance.DBInstanceIdentifier",
                "delete_action": "delete_db_instance",
                "delete_params": {"DBInstanceIdentifier": f"__PROJECT__-{safe_cid}-{i}", "SkipFinalSnapshot": True},
            })

        return ToolResult(
            node=ToolNode(id=cid, type="aws_aurora", label=label,
                          config=ToolNodeConfig(engine=engine, instance_type=inst_class)),
            boto3_config={"rds": configs},
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
        label = params.get("label", tid)
        hk = params.get("hash_key", "id")
        hk_type = params.get("hash_key_type", "S")
        billing = params.get("billing_mode", "PAY_PER_REQUEST")

        key_schema = [{"AttributeName": hk, "KeyType": "HASH"}]
        attr_defs = [{"AttributeName": hk, "AttributeType": hk_type}]

        if params.get("range_key"):
            rk = params["range_key"]
            key_schema.append({"AttributeName": rk, "KeyType": "RANGE"})
            attr_defs.append({"AttributeName": rk, "AttributeType": "S"})

        create_params = {
            "TableName": f"__PROJECT__-{tid}",
            "KeySchema": key_schema,
            "AttributeDefinitions": attr_defs,
            "BillingMode": billing,
            "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{tid}"}],
        }

        if billing == "PROVISIONED":
            create_params["ProvisionedThroughput"] = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

        configs = [{
            "service": "dynamodb",
            "action": "create_table",
            "params": create_params,
            "label": label,
            "resource_type": "aws_dynamodb",
            "resource_id_path": "TableDescription.TableArn",
            "delete_action": "delete_table",
            "delete_params": {"TableName": f"__PROJECT__-{tid}"},
            "waiter": "table_exists",
            "waiter_params": {"TableName": f"__PROJECT__-{tid}"},
        }]
        return ToolResult(
            node=ToolNode(id=tid, type="aws_dynamodb", label=label,
                          config=ToolNodeConfig(extra={"hash_key": hk, "billing_mode": billing})),
            boto3_config={"dynamodb": configs},
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
        label = params.get("label", cid)
        configs = [{
            "service": "redshift",
            "action": "create_cluster",
            "params": {
                "ClusterIdentifier": f"__PROJECT__-{cid}",
                "NodeType": params.get("node_type", "dc2.large"),
                "NumberOfNodes": params.get("number_of_nodes", 2),
                "DBName": params.get("db_name", "analytics"),
                "MasterUsername": "admin",
                "MasterUserPassword": "ChangeMe123!",
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{cid}"}],
            },
            "label": label,
            "resource_type": "aws_redshift",
            "resource_id_path": "Cluster.ClusterIdentifier",
            "delete_action": "delete_cluster",
            "delete_params": {"ClusterIdentifier": f"__PROJECT__-{cid}", "SkipFinalClusterSnapshot": True},
            "waiter": "cluster_available",
            "waiter_params": {"ClusterIdentifier": f"__PROJECT__-{cid}"},
        }]
        return ToolResult(
            node=ToolNode(id=cid, type="aws_redshift", label=label,
                          config=ToolNodeConfig(instance_type=params.get("node_type", "dc2.large"))),
            boto3_config={"redshift": configs},
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
        label = params.get("label", cid)
        engine = params.get("engine", "redis")
        safe_cid = cid.lower().replace("_", "-")
        configs = [{
            "service": "elasticache",
            "action": "create_cache_cluster",
            "params": {
                "CacheClusterId": f"__PROJECT__-{safe_cid}",
                "Engine": engine,
                "CacheNodeType": params.get("node_type", "cache.t3.micro"),
                "NumCacheNodes": params.get("num_cache_nodes", 1),
                "Port": 6379 if engine == "redis" else 11211,
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{safe_cid}"}],
            },
            "label": label,
            "resource_type": "aws_elasticache",
            "resource_id_path": "CacheCluster.CacheClusterId",
            "delete_action": "delete_cache_cluster",
            "delete_params": {"CacheClusterId": f"__PROJECT__-{safe_cid}"},
            "waiter": "cache_cluster_available",
            "waiter_params": {"CacheClusterId": f"__PROJECT__-{safe_cid}"},
        }]
        return ToolResult(
            node=ToolNode(id=cid, type="aws_elasticache", label=label,
                          config=ToolNodeConfig(engine=engine, instance_type=params.get("node_type", "cache.t3.micro"))),
            boto3_config={"elasticache": configs},
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
        label = params.get("label", nid)
        safe_nid = nid.lower().replace("_", "-")
        configs = [
            {
                "service": "neptune",
                "action": "create_db_cluster",
                "params": {
                    "DBClusterIdentifier": f"__PROJECT__-{safe_nid}",
                    "Engine": "neptune",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{safe_nid}"}],
                },
                "label": f"{label} — Cluster",
                "resource_type": "aws_neptune_cluster",
                "resource_id_path": "DBCluster.DBClusterIdentifier",
                "delete_action": "delete_db_cluster",
                "delete_params": {"DBClusterIdentifier": f"__PROJECT__-{safe_nid}", "SkipFinalSnapshot": True},
            },
            {
                "service": "neptune",
                "action": "create_db_instance",
                "params": {
                    "DBInstanceIdentifier": f"__PROJECT__-{safe_nid}-0",
                    "DBClusterIdentifier": f"__PROJECT__-{safe_nid}",
                    "DBInstanceClass": params.get("instance_class", "db.r5.large"),
                    "Engine": "neptune",
                },
                "label": f"{label} — Instance",
                "resource_type": "aws_neptune_instance",
                "resource_id_path": "DBInstance.DBInstanceIdentifier",
                "delete_action": "delete_db_instance",
                "delete_params": {"DBInstanceIdentifier": f"__PROJECT__-{safe_nid}-0"},
            },
        ]
        return ToolResult(
            node=ToolNode(id=nid, type="aws_neptune", label=label,
                          config=ToolNodeConfig(engine="neptune", instance_type=params.get("instance_class", "db.r5.large"))),
            boto3_config={"neptune": configs},
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
        label = params.get("label", did)
        safe_did = did.lower().replace("_", "-")
        inst_count = params.get("instances", 2)

        configs = [{
            "service": "docdb",
            "action": "create_db_cluster",
            "params": {
                "DBClusterIdentifier": f"__PROJECT__-{safe_did}",
                "Engine": "docdb",
                "MasterUsername": "admin",
                "MasterUserPassword": "ChangeMe123!",
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{safe_did}"}],
            },
            "label": f"{label} — Cluster",
            "resource_type": "aws_documentdb_cluster",
            "resource_id_path": "DBCluster.DBClusterIdentifier",
            "delete_action": "delete_db_cluster",
            "delete_params": {"DBClusterIdentifier": f"__PROJECT__-{safe_did}", "SkipFinalSnapshot": True},
        }]

        for i in range(inst_count):
            configs.append({
                "service": "docdb",
                "action": "create_db_instance",
                "params": {
                    "DBInstanceIdentifier": f"__PROJECT__-{safe_did}-{i}",
                    "DBClusterIdentifier": f"__PROJECT__-{safe_did}",
                    "DBInstanceClass": params.get("instance_class", "db.r5.large"),
                    "Engine": "docdb",
                },
                "label": f"{label} — Instance {i}",
                "resource_type": "aws_documentdb_instance",
                "resource_id_path": "DBInstance.DBInstanceIdentifier",
                "delete_action": "delete_db_instance",
                "delete_params": {"DBInstanceIdentifier": f"__PROJECT__-{safe_did}-{i}"},
            })

        return ToolResult(
            node=ToolNode(id=did, type="aws_documentdb", label=label,
                          config=ToolNodeConfig(engine="documentdb", instance_type=params.get("instance_class", "db.r5.large"))),
            boto3_config={"docdb": configs},
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
        label = params.get("label", kid)
        ks_name = params.get("keyspace_name", "app_keyspace")
        tbl_name = params.get("table_name", "data")
        configs = [
            {
                "service": "keyspaces",
                "action": "create_keyspace",
                "params": {
                    "keyspaceName": ks_name,
                    "tags": [{"key": "Name", "value": f"__PROJECT__-{kid}"}],
                },
                "label": f"{label} — Keyspace",
                "resource_type": "aws_keyspaces_keyspace",
                "resource_id_path": "resourceArn",
                "delete_action": "delete_keyspace",
                "delete_params": {"keyspaceName": ks_name},
            },
            {
                "service": "keyspaces",
                "action": "create_table",
                "params": {
                    "keyspaceName": ks_name,
                    "tableName": tbl_name,
                    "schemaDefinition": {
                        "allColumns": [{"name": "id", "type": "text"}],
                        "partitionKeys": [{"name": "id"}],
                    },
                },
                "label": label,
                "resource_type": "aws_keyspaces_table",
                "resource_id_path": "resourceArn",
                "delete_action": "delete_table",
                "delete_params": {"keyspaceName": ks_name, "tableName": tbl_name},
            },
        ]
        return ToolResult(
            node=ToolNode(id=kid, type="aws_keyspaces", label=label, config=ToolNodeConfig(engine="cassandra")),
            boto3_config={"keyspaces": configs},
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
        label = params.get("label", tid)
        configs = [
            {
                "service": "timestream-write",
                "action": "create_database",
                "params": {
                    "DatabaseName": f"__PROJECT__-{tid}",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{tid}"}],
                },
                "label": f"{label} — Database",
                "resource_type": "aws_timestream_database",
                "resource_id_path": "Database.Arn",
                "delete_action": "delete_database",
                "delete_params": {"DatabaseName": f"__PROJECT__-{tid}"},
            },
            {
                "service": "timestream-write",
                "action": "create_table",
                "params": {
                    "DatabaseName": f"__PROJECT__-{tid}",
                    "TableName": params.get("table_name", "metrics"),
                    "RetentionProperties": {
                        "MemoryStoreRetentionPeriodInHours": params.get("retention_hours", 24),
                        "MagneticStoreRetentionPeriodInDays": params.get("retention_days", 365),
                    },
                },
                "label": label,
                "resource_type": "aws_timestream_table",
                "resource_id_path": "Table.Arn",
                "delete_action": "delete_table",
                "delete_params": {"DatabaseName": f"__PROJECT__-{tid}", "TableName": params.get("table_name", "metrics")},
            },
        ]
        return ToolResult(
            node=ToolNode(id=tid, type="aws_timestream", label=label, config=ToolNodeConfig(engine="timestream")),
            boto3_config={"timestream-write": configs},
        )
