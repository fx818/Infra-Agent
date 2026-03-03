# Infra-Agent — AI-Powered AWS Infrastructure Automation

> Design, visualize, and deploy AWS infrastructure through natural language chat **or** a drag-and-drop canvas — no Terraform, no manual boto3 calls.

---

## Table of Contents

1. [What Is Infra-Agent?](#what-is-infra-agent)
2. [Core Features](#core-features)
3. [How It Works — End-to-End Flow](#how-it-works--end-to-end-flow)
4. [AI Agent Pipeline](#ai-agent-pipeline)
5. [Drag-and-Drop Builder](#drag-and-drop-builder)
6. [Deployment Engine](#deployment-engine)
7. [AWS Explorer](#aws-explorer)
8. [Monitoring & Cost Analysis](#monitoring--cost-analysis)
9. [Tech Stack](#tech-stack)
10. [Project Structure](#project-structure)
11. [API Reference](#api-reference)
12. [Database Models](#database-models)
13. [Getting Started](#getting-started)
14. [Environment Variables](#environment-variables)
15. [Configuration — LLM Provider](#configuration--llm-provider)
16. [Configuration — AWS Credentials](#configuration--aws-credentials)

---

## What Is Infra-Agent?

Infra-Agent is a full-stack web application that lets you build and deploy real AWS infrastructure in two ways:

- **Chat (NL2I)** — describe your system in plain English ("build a scalable REST API with DynamoDB and a Lambda function") and a multi-agent AI pipeline designs the architecture, estimates cost, generates a visual graph, and produces deployment-ready boto3 configuration — all in one request.
- **Drag-and-Drop Canvas** — pick AWS service tiles from a categorized sidebar, drop them onto a canvas, draw connections, configure node properties, and save the project. The system deterministically translates your canvas into boto3 deployment configs without needing the LLM.

Both paths converge on the same **Deployment Engine**: a boto3-based executor that creates real AWS resources in your account, streams live logs back to the browser via Server-Sent Events, tracks resource IDs/ARNs in a local state file, and can destroy everything in one click.

---

## Core Features

| Feature | Description |
|---|---|
| **Natural Language → AWS** | Describe any architecture in plain English; AI creates nodes, edges, cost estimate, and deployment config |
| **AI Chat Editing** | Ask follow-up questions to add/remove/change services; the graph and deployment config update automatically |
| **Drag-and-Drop Canvas** | 50+ AWS services in a searchable, categorized sidebar; validated connection rules between services |
| **Interactive Architecture Graph** | React Flow canvas with minimap, zoom, fullscreen, and a "Code" tab showing raw boto3 configs |
| **Real Resource Deployment** | Boto3 executor creates real AWS resources; streams live logs to the browser |
| **EC2 Key Pair Automation** | Auto-creates a PEM key pair for every EC2 instance; downloadable from the UI; SSH instructions shown |
| **Live Deployment Logs** | SSE streaming from backend → browser; progress counters, success/failure per resource |
| **Destroy on Click** | Full teardown using stored resource IDs; respects dependency order |
| **AWS Explorer** | Discover *all* AWS resources across all regions (EC2, S3, Lambda, RDS, ECS, and more) — even ones not created by Infra-Agent — with bulk delete |
| **CloudWatch Monitoring** | Per-project real-time metrics (CPU, invocations, latency, error rate) from CloudWatch |
| **Cost Estimation** | AI-powered monthly cost breakdown by service; shown before and after every architecture change |
| **Cost Analysis Dashboard** | Cross-project cost trends, top-spender ranking, savings recommendations |
| **Request Logger** | Every API request/response is appended to a daily CSV (`logs/api_requests_YYYY-MM-DD.csv`) |
| **Multi-User Auth** | JWT-based auth; per-user encrypted AWS credentials and LLM API key storage |
| **LLM Agnostic** | Works with OpenAI, Azure OpenAI, Anthropic (via proxy), Ollama, vLLM, or any OpenAI-compatible endpoint |

---

## How It Works — End-to-End Flow

### Path 1 — Natural Language (Chat UI)

```
User types: "Build a web app with EC2, RDS PostgreSQL, and an S3 bucket for media"
                              │
                              ▼
                    ┌─────────────────┐
                    │  Intent Agent   │  Extracts: app_type, scale, latency, storage
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Tool Agent     │  LLM calls tools: create_ec2_instance(),
                    │  (main design)  │  create_rds_instance(), create_s3_bucket()…
                    └────────┬────────┘
                             │  produces ArchitectureGraph + boto3 configs
                             ▼
              ┌──────────────────────────────┐
              │  Cost Agent  │  Visual Agent │  Parallel: cost estimate + React Flow layout
              └──────────────────────────────┘
                             │
                             ▼
                    Saved to database (Architecture v1)
                    Returned to frontend: graph + cost + visual
                             │
                             ▼
                    User sees: interactive diagram + cost breakdown
                    User clicks "Deploy" →
                             │
                             ▼
                    ┌─────────────────┐
                    │ Boto3 Executor  │  Creates real AWS resources via boto3
                    │  (SSE stream)   │  Streams progress logs to browser
                    └─────────────────┘
```

### Path 2 — Drag-and-Drop Canvas

```
User opens Drag-Build page
User drags "EC2", "RDS", "VPC" tiles onto canvas
User draws connections between nodes
User clicks "Save Project"
                    │
                    ▼
      _generate_boto3_config() — deterministic, no LLM needed
      Converts each canvas node → boto3 API call config
      Saves Architecture record to database
                    │
                    ▼
      User goes to project → Deploy tab → clicks Deploy
                    │
                    ▼
      Boto3 Executor → real AWS resources
```

### Path 3 — AI Edit of an Existing Project

```
User opens any project (AI or drag-built)
Types in chat: "Add an ElastiCache Redis cluster between EC2 and RDS"
                    │
                    ▼
              Edit Agent (modifies the ArchitectureGraph)
                    │
                    ▼
      If drag_built → _generate_boto3_config() (deterministic)
      If ai_generated → ToolAgent (LLM tool calls)
                    │
                    ▼
      New Architecture version saved
      Graph, cost, and visual update in UI
```

---

## AI Agent Pipeline

Six specialized agents are chained in sequence. Each is a stateless class with a single `async run()` method and reads its system prompt from a Markdown file in `backend/app/prompts/`.

| # | Agent | File | Input | Output | Purpose |
|---|---|---|---|---|---|
| 1 | **Intent Agent** | `intent_agent.py` | Natural language string | `IntentOutput` (app_type, scale, latency, storage_type, realtime, constraints) | Parses free text into structured intent for downstream agents |
| 2 | **Tool Agent** | `tool_agent.py` | `IntentOutput` + user prompt | `ArchitectureGraph` + `boto3_configs` dict | Main design agent — LLM calls registered tools to create each AWS service; assembles graph and deployment config |
| 3 | **Edit Agent** | `edit_agent.py` | `ArchitectureGraph` + modification prompt | Modified `ArchitectureGraph` | Conversationally edits an existing graph — adds/removes/modifies nodes and edges |
| 4 | **Cost Agent** | `cost_agent.py` | `ArchitectureGraph` | `CostEstimate` (per-service breakdown) | Estimates monthly AWS costs with free-tier consideration |
| 5 | **Visual Agent** | `visual_agent.py` | `ArchitectureGraph` | `VisualGraph` (React Flow JSON with positions, colors, icons) | Produces layout data for the interactive diagram |
| 6 | **Architecture Agent** | `architecture_agent.py` | `IntentOutput` | `ArchitectureGraph` | Legacy: direct graph design without tool calling (used in some flows) |

### LLM Tool Registry

The `ToolRegistry` (`app/tools/registry.py`) auto-discovers all tool classes across these packages:

| Package | Tools included |
|---|---|
| `compute` | EC2, Lambda, ECS/Fargate, EKS, App Runner, Elastic Beanstalk, Batch, Lightsail, Outposts |
| `storage` | S3, EBS |
| `databases` | RDS, DynamoDB, ElastiCache, Redshift |
| `networking` | VPC, Subnet, Security Group, ELB/ALB, CloudFront, API Gateway, Route53, NAT Gateway, Transit Gateway, Direct Connect |
| `security` | IAM, Cognito, Secrets Manager, WAF, ACM |
| `messaging` | SQS, SNS, Kinesis, EventBridge |
| `monitoring` | CloudWatch |
| `analytics` | Athena, Glue |
| `devops` | CloudFormation, ECR |
| `application` | Elastic Beanstalk env |

Each tool class extends `BaseTool` and exposes:
- A JSON schema describing its parameters (shown to the LLM)
- An `execute(params)` method that returns a boto3 config dict

---

## Drag-and-Drop Builder

The canvas (`/drag-build`) is built on **React Flow** and provides a full visual infrastructure design environment.

### Service Catalog

All AWS services are defined in `frontend/src/utils/awsServiceCatalog.ts` and organized into categories:
- Compute, Storage, Database, Networking, Security, Messaging, Analytics, DevOps, Monitoring

Each service entry includes: display name, node type string (e.g. `aws_ec2`), description, configurable properties (instance type, runtime, engine, memory, etc.), and official AWS color.

### Connection Validation

`frontend/src/utils/awsConnections.ts` encodes which services are allowed to connect to which. Attempted connections that violate rules (e.g., connecting two VPCs directly) are blocked with an error toast. Valid connections automatically get a meaningful label (e.g., "reads/writes", "triggers", "stores data").

### Canvas Interactions

- **Drag from sidebar** → drop onto canvas instantiates a node
- **Click node** → select and configure properties in a side panel
- **Draw edge** between two nodes → validated connection
- **Undo** button reverts the last node addition
- **Search** in the sidebar filters services live
- **Save** serializes nodes + edges → `POST /drag-build/save` or `PUT /drag-build/update/{id}`

### Boto3 Config Generation

`_generate_boto3_config()` in `app/api/drag_build.py` is a deterministic mapper. It converts each canvas node type to the exact boto3 API call(s) needed. For example:

- `aws_ec2` → `ec2.run_instances` with `ImageId`, `InstanceType`, `TagSpecifications`
- `aws_rds` → `rds.create_db_instance` with engine, class, storage, credentials
- `aws_lambda` → `iam.create_role` (execution role) + `lambda.create_function`
- `aws_ecs` → `ecs.create_cluster` + `iam.create_role` (task execution) + `ecs.register_task_definition`
- `aws_vpc` → `ec2.create_vpc` + `ec2.create_internet_gateway`

Resource names are sanitized against each AWS service's naming rules before the config is stored.

---

## Deployment Engine

### Overview

The Boto3 Executor (`app/services/boto3/executor.py`) is the core deployment engine. It processes an ordered list of boto3 config dicts and executes them sequentially, streaming log lines back to the frontend via SSE.

### Execution Flow

1. **Placeholder substitution** — `__PROJECT__`, `__REGION__`, `__RESOURCE_ID__`, `__RESOLVE_PREV__` tokens are replaced with real values (sanitized project name, region, previously-created resource IDs)
2. **Pre-flight sanitization** — per-service name cleaners ensure names comply with AWS constraints (S3 lowercase + no underscores; DynamoDB `[a-zA-Z0-9_.-]+`; RDS alphanumeric + hyphen, starts with letter; ECS alphanumeric + underscore/hyphen; ElastiCache lowercase + hyphen; App Runner; CloudFormation)
3. **EC2 key pair auto-creation** — before every `run_instances` call, a fresh PEM key pair is created (or deleted + recreated if it already exists) so the user always gets a downloadable `.pem` file
4. **RDS auto-networking** — if RDS/Aurora is deployed without a `DBSubnetGroupName`, the executor auto-creates a VPC, subnets, security group, and DB subnet group
5. **API call** — the boto3 client call is made; resource ID extracted via `resource_id_path` JSON path
6. **CloudTrail tagging** — resources are tagged with `CreatedBy: Infra-Agent`, `Project`, `ManagedBy`
7. **IAM role propagation** — after IAM role creation, a waiter ensures the role is ready before dependent resources use it
8. **Waiters** — for services that need time (RDS `db_instance_available`, ECS cluster, etc.) the executor waits
9. **EC2 public IP** — after `run_instances`, an explicit `instance_running` waiter runs, then `describe_instances` fetches the real public IP and DNS
10. **LLM-assisted repair** — if a call fails with a fixable error (e.g., invalid parameter format), an LLM repair call attempts to fix the params and retry once
11. **State persistence** — all resource IDs, ARNs, public IPs, key pair names, and PEM material are written to `resource_state_json` on the `Deployment` record

### Destroy Flow

The State Tracker (`app/services/boto3/state_tracker.py`) reads the saved resource state and builds a reverse-ordered teardown plan. Calling `destroy_from_state()` deletes resources in the correct dependency order via their stored `delete_action` + `delete_params`.

### SSE Log Streaming

Deployment logs are streamed as `text/event-stream` from `POST /projects/{id}/deploy`. Each log line is a `data:` event containing a UTF-8 string. The frontend `DeploymentTab.tsx` consumes the stream and appends lines to a scrolling terminal-style log viewer.

---

## EC2 Connections

When an EC2 instance is deployed, the **EC2 Connection Info** panel in the Deploy tab shows:

- **Key pair name** and a **Download .pem** button (downloads directly from the backend)
- **Public IP** (polled after the instance reaches `running` state)
- **Public DNS** (if assigned)
- **SSH commands** for Amazon Linux and Ubuntu, with copy buttons
- `chmod 400` reminder

---

## AWS Explorer

The AWS Explorer (`/aws-explorer`) is a read/delete dashboard for all your AWS resources — including ones **not** created by Infra-Agent.

- Select any region from a dropdown (all regions fetched live from the AWS API)
- Fetches EC2 instances, S3 buckets, Lambda functions, RDS instances, ECS clusters, DynamoDB tables, SQS queues, SNS topics, CloudFront distributions, ElastiCache clusters, API Gateway APIs, App Runner services, VPCs, and Load Balancers
- Each resource shows: ID, name, type/engine/runtime, state (color-coded), launch/creation time
- **Bulk delete**: check any resources → "Delete Selected" → confirmed deletion via the appropriate AWS API
- Search/filter within fetched results

---

## Monitoring & Cost Analysis

### Per-Project Monitoring (`MonitoringTab`)

Reads CloudWatch metrics for resources deployed in a project:
- **Lambda**: invocations, errors, duration, throttles
- **RDS**: CPU utilization, connections, free storage, read/write latency
- Other resource types return a "no specialized metrics" placeholder

### Global Monitoring Dashboard (`/monitoring`)

Cross-project view of recent deployments, resource counts, failure trends.

### Cost Estimation

Every architecture generation/edit runs the `CostAgent` which uses the LLM to estimate monthly costs based on service types and scale. The result is a per-service cost breakdown displayed in the Architecture tab.

### Cost Analysis Dashboard (`/cost-analysis`)

- Total spend across all projects
- Top-spending projects ranked
- Monthly trend chart
- Savings recommendations (flags over-provisioned resources, suggests reserved instances, etc.)

---

## Tech Stack

### Backend — Python

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.110+ | API framework — REST endpoints + SSE streaming |
| `uvicorn` | 0.29+ | ASGI server |
| `sqlalchemy` | 2.0+ (async) | ORM for all database models |
| `aiosqlite` | latest | Async SQLite driver (dev/default) |
| `asyncpg` | latest | Async PostgreSQL driver (production) |
| `alembic` | latest | Database schema migrations |
| `pydantic` | v2 | Request/response schema validation |
| `pydantic-settings` | v2 | `.env` configuration loader |
| `python-jose[cryptography]` | latest | JWT token creation and verification |
| `passlib[bcrypt]` | latest | Password hashing |
| `cryptography` | latest | AES encryption for stored credentials |
| `boto3` | latest | AWS SDK — creates, updates, deletes all AWS resources |
| `botocore` | latest | Boto3 core / waiter support |
| `openai` | latest | OpenAI-compatible LLM client (used for all agents) |
| `redis` | latest | Redis client (task queue + caching) |
| `httpx` | latest | Async HTTP client (internal requests) |
| `python-multipart` | latest | Multipart form data (file upload support) |
| `aiofiles` | latest | Async file I/O |
| `python-dotenv` | latest | Loads `.env` in development |

### Frontend — JavaScript / TypeScript

| Package | Version | Purpose |
|---|---|---|
| `react` | 18 | UI framework |
| `react-dom` | 18 | DOM renderer |
| `typescript` | 5+ | Static typing |
| `vite` | 5+ | Build tool + dev server (HMR) |
| `@xyflow/react` | latest | React Flow — interactive graph canvas for both architecture view and drag-build |
| `tailwindcss` | 3 | Utility-first CSS framework |
| `postcss` | latest | CSS post-processor (for Tailwind) |
| `axios` | latest | HTTP client with JWT interceptor |
| `react-router-dom` | v6 | Client-side routing |
| `lucide-react` | latest | Icon library (all UI icons) |
| `eslint` | latest | Linting |
| `@vitejs/plugin-react` | latest | Vite plugin for React JSX transform |
| `@types/react` | latest | TypeScript types for React |
| `@types/react-dom` | latest | TypeScript types for React DOM |

### Infrastructure / Runtime

| Technology | Role |
|---|---|
| **Redis** | Background task queue; session caching; used by deployment task workers |
| **SQLite** | Default embedded database (`nl2i.db`) — zero config, auto-created on startup |
| **PostgreSQL** | Production database (swap `DATABASE_URL` in `.env`) |
| **Python 3.12** | Backend runtime |
| **Node.js 18+** | Frontend build toolchain |
| **Uvicorn** | ASGI server running FastAPI |

### AWS Services Used by the Application

These are the AWS services that **Infra-Agent itself uses** to build and manage infrastructure in your account:

#### Compute
| Service | How It's Used |
|---|---|
| **EC2** | Deploy virtual machines; auto-creates key pairs; waits for `instance_running` then reads public IP |
| **Lambda** | Deploy serverless functions (Python, Node.js, Java, etc.); IAM execution role auto-created |
| **ECS** | Deploy containerized workloads via clusters + task definitions + services |
| **EKS** | Provision Kubernetes clusters + node groups |
| **App Runner** | Deploy containerized apps without managing infrastructure |
| **AWS Fargate** | Serverless container runtime for ECS tasks |
| **Elastic Beanstalk** | PaaS deployment for web applications |
| **AWS Batch** | Managed batch computing environments and job queues |
| **Lightsail** | Simplified VM + fixed-price instances |
| **AWS Outposts** | On-premises AWS infrastructure *(schema support)* |

#### Storage
| Service | How It's Used |
|---|---|
| **Amazon S3** | Object storage buckets; name sanitized (lowercase, no underscores, max 63 chars) |
| **Amazon EBS** | Block storage volumes for EC2 instances |

#### Database
| Service | How It's Used |
|---|---|
| **Amazon RDS** | Managed relational databases (MySQL, PostgreSQL, MariaDB, Oracle, SQL Server, Aurora); auto-networking (VPC + subnet group + SG) if not provided |
| **Amazon Aurora** | MySQL/PostgreSQL-compatible managed database clusters |
| **Amazon DynamoDB** | Managed NoSQL tables with configurable billing mode and GSIs |
| **Amazon ElastiCache** | In-memory caching clusters (Redis, Memcached) |
| **Amazon Redshift** | Managed data warehouse clusters |

#### Networking
| Service | How It's Used |
|---|---|
| **Amazon VPC** | Virtual private clouds; auto-created when required by RDS/ECS |
| **Subnets** | Public and private subnets within VPCs |
| **Security Groups** | Firewall rules for EC2, RDS, Lambda, etc. |
| **Elastic Load Balancing (ALB/NLB)** | Application and Network load balancers |
| **Amazon CloudFront** | CDN distributions fronting S3 or custom origins |
| **Amazon API Gateway** | HTTP and WebSocket API management (v2) |
| **Amazon Route 53** | DNS hosted zones and records |
| **NAT Gateway** | Outbound internet for private subnet resources |
| **AWS Transit Gateway** | Hub-and-spoke VPC connectivity |
| **AWS Direct Connect** | Dedicated network connections *(schema support)* |

#### Security & Identity
| Service | How It's Used |
|---|---|
| **AWS IAM** | Roles and policies auto-created for Lambda, ECS task execution, EC2 instance profiles, etc. |
| **Amazon Cognito** | User pools and identity pools for app auth |
| **AWS Secrets Manager** | Secure secrets storage |
| **AWS WAF** | Web ACLs for API Gateway / CloudFront |
| **AWS Certificate Manager (ACM)** | SSL/TLS certificates |

#### Messaging & Streaming
| Service | How It's Used |
|---|---|
| **Amazon SQS** | Message queues (Standard and FIFO) |
| **Amazon SNS** | Pub/sub notification topics |
| **Amazon Kinesis** | Data streams for real-time pipelines |
| **Amazon EventBridge** | Event buses and rules |

#### DevOps & Containers
| Service | How It's Used |
|---|---|
| **AWS CloudFormation** | Infrastructure as code stacks *(StackName sanitized)* |
| **Amazon ECR** | Container image registries |

#### Monitoring & Analytics
| Service | How It's Used |
|---|---|
| **Amazon CloudWatch** | Metrics pulled for per-project monitoring dashboards (CPU, invocations, latency, errors) |
| **Amazon Athena** | Serverless query service *(schema support)* |
| **AWS Glue** | ETL catalog and jobs *(schema support)* |

#### Discovered by AWS Explorer (read + delete)
| Service | |
|---|---|
| EC2, S3, Lambda, RDS | ✓ |
| ECS Clusters, DynamoDB | ✓ |
| SQS, SNS | ✓ |
| CloudFront, ElastiCache | ✓ |
| API Gateway, App Runner | ✓ |
| VPCs, Load Balancers | ✓ |

---

## Project Structure

```
Infra-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, middleware, router registration
│   │   ├── core/
│   │   │   ├── config.py            # All env settings via pydantic-settings
│   │   │   ├── deps.py              # FastAPI dependency injection (db, current_user)
│   │   │   └── security.py          # JWT, password hashing, credential encryption
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py              # User (auth, LLM key, AWS creds)
│   │   │   ├── project.py           # Project (name, region, source: ai_generated/drag_built)
│   │   │   ├── architecture.py      # Architecture (versioned: graph, visual, terraform_files, cost)
│   │   │   ├── deployment.py        # Deployment (status, logs, resource_state_json)
│   │   │   └── chat.py              # ChatMessage (per-project conversation history)
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── api/                     # FastAPI routers
│   │   │   ├── auth.py              # /auth/register, /auth/login, /auth/me
│   │   │   ├── projects.py          # /projects CRUD
│   │   │   ├── architecture.py      # /projects/{id}/generate, /edit, /architecture, /cost
│   │   │   ├── deployment.py        # /projects/{id}/deploy, /destroy, /status, /deployments
│   │   │   ├── drag_build.py        # /drag-build/save, /drag-build/update/{id}
│   │   │   ├── aws_explorer.py      # /aws/regions, /aws/resources, /aws/delete
│   │   │   ├── monitoring.py        # /projects/{id}/metrics
│   │   │   ├── cost_analysis.py     # /cost-analysis/summary, /recommendations
│   │   │   ├── config.py            # /config (user LLM + AWS preferences)
│   │   │   ├── logs.py              # /logs (serve CSV log files)
│   │   │   └── websocket.py         # WS /projects/{id}/logs (legacy)
│   │   ├── services/
│   │   │   ├── ai/                  # All AI agents
│   │   │   │   ├── base.py          # OpenAICompatibleProvider (generate, generate_with_tools)
│   │   │   │   ├── intent_agent.py
│   │   │   │   ├── tool_agent.py    # Main design agent (LLM tool calling loop)
│   │   │   │   ├── edit_agent.py
│   │   │   │   ├── cost_agent.py
│   │   │   │   ├── visual_agent.py
│   │   │   │   └── architecture_agent.py
│   │   │   ├── boto3/
│   │   │   │   ├── executor.py      # Core deployment engine (~1200 lines)
│   │   │   │   └── state_tracker.py # Resource state read/write for destroy
│   │   │   └── aws/
│   │   │       ├── cloudwatch.py    # CloudWatch metrics fetcher
│   │   │       └── cost_estimator.py# Static price table for cost hints
│   │   ├── tools/                   # LLM-callable tool classes (50+ AWS services)
│   │   │   ├── registry.py          # Auto-discovers and registers all tools
│   │   │   ├── base.py              # BaseTool abstract class
│   │   │   ├── compute/             # EC2, Lambda, ECS, EKS, App Runner, Batch…
│   │   │   ├── storage/             # S3, EBS
│   │   │   ├── databases/           # RDS, DynamoDB, ElastiCache, Redshift
│   │   │   ├── networking/          # VPC, Subnet, SG, ELB, CloudFront, API GW…
│   │   │   ├── security/            # IAM, Cognito, Secrets Manager, WAF, ACM
│   │   │   ├── messaging/           # SQS, SNS, Kinesis, EventBridge
│   │   │   ├── monitoring/          # CloudWatch
│   │   │   ├── analytics/           # Athena, Glue
│   │   │   ├── devops/              # CloudFormation, ECR
│   │   │   └── connect_services.py  # Tool for LLM to declare connections (edges)
│   │   ├── prompts/                 # LLM system prompts (Markdown)
│   │   │   ├── tool_agent_prompt.md
│   │   │   ├── intent_agent_prompt.md
│   │   │   ├── architecture_agent_prompt.md
│   │   │   ├── edit_agent_prompt.md
│   │   │   ├── cost_agent_prompt.md
│   │   │   └── visual_agent_prompt.md
│   │   ├── middleware/
│   │   │   └── request_logger.py    # Logs every request/response to daily CSV
│   │   └── utils/
│   │       ├── validators.py        # sanitize_boto3_config, validate_architecture_graph
│   │       └── prompt_loader.py     # Loads .md prompt files
│   ├── alembic/                     # Database migrations
│   ├── workspaces/                  # Per-project workspace directories (resource state)
│   ├── logs/                        # Daily CSV API request logs
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── pages/
        │   ├── Dashboard.tsx        # Project list with status badges
        │   ├── DragBuild.tsx        # Full drag-and-drop canvas builder (~725 lines)
        │   ├── AWSExplorer.tsx      # AWS resource discovery + bulk delete
        │   ├── CostAnalysis.tsx     # Cross-project cost dashboard
        │   ├── Monitoring.tsx       # Global monitoring overview
        │   ├── Settings.tsx         # AWS credentials + LLM config + preferences
        │   ├── Deployments.tsx      # Cross-project deployment history
        │   ├── Logs.tsx             # API request log viewer
        │   └── projects/
        │       ├── ProjectDetail.tsx     # Tabbed project view (Architecture / Deploy / Monitor)
        │       ├── ArchitectureTab.tsx   # Chat input, message history, graph/code view
        │       ├── DeploymentTab.tsx     # Deploy/Destroy, SSE log stream, EC2 key info
        │       └── MonitoringTab.tsx     # Per-project CloudWatch metrics
        ├── components/
        │   ├── Layout.tsx           # Sidebar navigation
        │   ├── projects/
        │   │   └── BlueprintGraph.tsx   # React Flow wrapper (fullscreen, minimap, controls)
        │   └── drag-build/
        │       └── DragBuildNode.tsx    # Custom React Flow node for drag-build canvas
        ├── api/                     # Axios API client modules
        ├── utils/
        │   ├── awsServiceCatalog.ts # 50+ AWS service definitions + categories
        │   ├── awsConnections.ts    # Connection validation rules between services
        │   └── awsLogos.ts          # SVG/color logo map per service type
        ├── types/                   # TypeScript interfaces
        └── context/
            └── AuthContext.tsx      # JWT auth context + token storage
```

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login → returns JWT access token |
| `GET` | `/auth/me` | Get current user profile |

### Projects

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/projects` | List all user projects |
| `POST` | `/projects` | Create a new empty project |
| `GET` | `/projects/{id}` | Get project details |
| `PUT` | `/projects/{id}` | Update project metadata |
| `DELETE` | `/projects/{id}` | Delete project and all its data |

### Architecture

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/projects/{id}/generate` | Run full AI pipeline (NL → architecture + boto3 + cost + visual) |
| `POST` | `/projects/{id}/edit` | Edit existing architecture via chat prompt |
| `GET` | `/projects/{id}/architecture` | Get latest architecture, graph, and deployment config |
| `GET` | `/projects/{id}/cost` | Get cost estimate for the current architecture |
| `GET` | `/projects/{id}/messages` | Get chat message history |

### Deployment

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/projects/{id}/deploy` | Deploy infrastructure (SSE stream of log lines) |
| `POST` | `/projects/{id}/destroy` | Destroy all deployed resources (SSE stream) |
| `GET` | `/projects/{id}/status` | Get current deployment status |
| `GET` | `/projects/{id}/deployments` | List all deployment history for a project |
| `GET` | `/projects/{id}/ec2-keys` | List EC2 instances with key pair + public IP info |
| `GET` | `/projects/{id}/ec2-key/{name}/download` | Download PEM file for an EC2 key pair |

### Drag-Build

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/drag-build/save` | Save a new drag-and-drop project |
| `PUT` | `/drag-build/update/{id}` | Update existing drag-build project canvas |

### AWS Explorer

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/aws/regions` | List all available AWS regions |
| `GET` | `/aws/resources?region=us-east-1` | Discover all resources in a region |
| `POST` | `/aws/delete` | Delete specified resources by type + ID |

### Monitoring & Config

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/projects/{id}/metrics` | Get CloudWatch metrics for deployed resources |
| `GET` | `/cost-analysis/summary` | Cross-project cost summary |
| `GET` | `/config` | Get user preferences and LLM config |
| `PUT` | `/config` | Update preferences |
| `PUT` | `/config/aws-credentials` | Store encrypted AWS credentials |
| `PUT` | `/config/llm` | Store encrypted LLM API key + provider settings |
| `GET` | `/logs` | List available log files |
| `GET` | `/logs/{filename}` | Stream a CSV log file |

---

## Database Models

| Model | Key Fields |
|---|---|
| `User` | `email`, `hashed_password`, `aws_credentials_encrypted`, `llm_api_key_encrypted`, `llm_preferences` (JSON with `base_url`, `model`) |
| `Project` | `name`, `description`, `region`, `status` (created/generating/ready/deploying/deployed/failed), `source` (ai_generated/drag_built) |
| `Architecture` | `version` (auto-incrementing), `intent_json`, `graph_json`, `terraform_files_json` (actually boto3 configs), `cost_json`, `visual_json` |
| `Deployment` | `action` (deploy/destroy), `status`, `log_output`, `resource_state_json` (all created resource IDs, ARNs, IPs, PEM material) |
| `ChatMessage` | `role` (user/assistant), `content`, `architecture_version` |

Every architecture edit creates a **new version** — full history is preserved.

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Redis (for task queue)
- An AWS account with programmatic access
- An LLM API key (OpenAI, or any compatible provider)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/Infra-Agent.git
cd Infra-Agent
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — see Environment Variables section below

# Run the server
uvicorn app.main:app --reload --port 8000
```

The database (`nl2i.db`) is created automatically on first startup via SQLAlchemy's `create_all`.

### 3. Frontend setup

```bash
cd frontend

npm install
npm run dev        # Development server on http://localhost:5173
```

### 4. Redis

```bash
# macOS
brew install redis && brew services start redis

# Ubuntu/Debian
sudo apt install redis-server && sudo systemctl start redis

# Windows — use Redis for Windows from /redis/ directory in this repo
redis-server redis/redis.windows.conf
```

### 5. Open the app

Navigate to `http://localhost:5173`. Register an account, then go to **Settings** to configure your AWS credentials and LLM API key.

---

## Environment Variables

Create `backend/.env`:

```env
# ── Application ─────────────────────────────────
APP_NAME=NL2I Backend
APP_VERSION=1.0.0
DEBUG=false

# ── Database ─────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./nl2i.db
# For PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/nl2i

# ── Redis ────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── JWT Auth ─────────────────────────────────────
SECRET_KEY=your-random-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

# ── Default LLM Provider (can be overridden per-user via Settings) ──
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o

# ── Default AWS Credentials (can be overridden per-user via Settings) ──
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# ── Security ─────────────────────────────────────
# 32-byte base64-encoded key for encrypting stored credentials
CREDENTIAL_ENCRYPTION_KEY=your-32-byte-base64-key
```

---

## Configuration — LLM Provider

All LLM settings can be configured per-user in the **Settings → AI Configuration** tab. The backend calls `decrypt_credentials()` on the stored key and constructs an `OpenAICompatibleProvider` with the user's `base_url` and `model`.

**Supported providers:**

| Provider | `LLM_BASE_URL` | Notes |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | Default |
| Azure OpenAI | `https://{resource}.openai.azure.com/openai/deployments/{deployment}` | |
| Anthropic (via proxy) | `https://api.anthropic.com/v1` | Requires compatible proxy |
| Ollama (local) | `http://localhost:11434/v1` | Set `LLM_API_KEY=ollama` |
| vLLM | `http://localhost:8000/v1` | |
| Any OpenAI-compatible | Custom URL | |

Recommended models: `gpt-4o`, `gpt-4o-mini`, `claude-3-5-sonnet`, `llama-3.3-70b`

---

## Configuration — AWS Credentials

AWS credentials can be set globally (`.env`) or per-user (encrypted in the database via **Settings → AWS Credentials**). Per-user credentials take precedence.

The minimum IAM permissions required for full functionality:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*", "s3:*", "rds:*", "lambda:*", "dynamodb:*",
        "ecs:*", "iam:*", "elasticache:*", "sqs:*", "sns:*",
        "cloudfront:*", "route53:*", "apigateway:*", "logs:*",
        "cloudwatch:*", "secretsmanager:*", "eks:*", "ecr:*",
        "elasticloadbalancing:*", "events:*", "kinesis:*",
        "redshift:*", "cognito-idp:*", "apprunner:*",
        "cloudformation:*", "cloudtrail:*"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Security note**: In production, scope permissions down to specific resources. All credentials are encrypted at rest using a symmetric key (`CREDENTIAL_ENCRYPTION_KEY`). Never commit `.env` to version control.
