# Infra-Agent — Product Requirements Document

Author: Anurag Upadhyay\
Version: 2.0\
Date: March 2026\
Status: Live — actively developed

---

# 1. Executive Summary

Infra-Agent is an AI-powered AWS infrastructure automation platform that lets developers design, deploy, monitor, and manage real cloud infrastructure through natural language chat or a visual drag-and-drop canvas — without writing Terraform, CloudFormation, or raw boto3 code.

The platform ships a multi-agent AI pipeline (7 agents, 88 AWS service tools), a boto3-based deployment engine with live SSE log streaming, an AWS Resource Explorer, a Cost Analysis dashboard backed by AWS Cost Explorer, and CloudWatch monitoring — all accessible through a polished React + Tailwind dark-mode UI.

**One-liner:** *Talk to your infrastructure. Deploy it in one click.*

---

# 2. Product Vision

**Short-term (current):** Enable any developer to go from an English sentence to running AWS infrastructure in under five minutes — no DevOps knowledge required.

**Mid-term (6–12 months):** Become the default tool startups use to stand up, iterate, and tear down AWS environments during rapid product development.

**Long-term (18+ months):** Expand into a full AI DevOps operating system — multi-cloud, autonomous optimization, self-healing, and predictive scaling — so that infrastructure manages itself.

> *"Developers define what they need. Infra-Agent figures out the how."*

---

# 3. Problem Statement

### 3.1 Infrastructure Is Still the Bottleneck

AI code-generation tools have collapsed the time to write application code. But deploying that code still requires configuring compute, networking, storage, databases, load balancers, security groups, and monitoring — skills most developers don't have and most startups can't afford to hire for.

### 3.2 Cost Visibility Comes Too Late

Startups discover their AWS bill is too high *after* the fact. There is no pre-deployment cost signal and no easy way to compare service tiers or right-size resources.

### 3.3 Teardown Is Dangerous

Cloud resources are interdependent. Deleting them manually risks orphaned resources, dangling security groups, and surprise billing. Startups need one-click, dependency-aware teardown.

### 3.4 Context Switching Kills Velocity

Developers bounce between the AWS Console, CLI, IaC files, and monitoring dashboards. A single pane of glass — chat, canvas, deploy, monitor — eliminates that overhead.

---

# 4. Target Market

### Primary — Startup & Solo Developers

| Persona | Description | Key Need |
|---------|-------------|----------|
| **Indie / Solo Developer** | Building side projects or micro-SaaS; no DevOps teammate | Deploy fast, keep costs near zero |
| **Startup Founder (Technical)** | Shipping an MVP with 1–3 engineers | Go from idea to production infra in minutes, iterate daily |
| **AI / ML Builder** | Training models, deploying inference endpoints | Spin up GPU instances, S3 buckets, Lambda pipelines without console juggling |
| **Hackathon Participant** | Needs live infra in hours, not days | Instant deploy + teardown |

### Secondary — Professional DevOps

| Persona | Description | Key Need |
|---------|-------------|----------|
| **DevOps Engineer** | Manages production systems across teams | Automate repetitive provisioning; get cost recommendations |
| **Cloud Architect** | Designs reference architectures for clients | Quick prototyping + cost estimation before committing to IaC |
| **Engineering Manager** | Oversees infra spend across projects | Centralized cost dashboard + savings recommendations |

---

# 5. Core Product Features (Implemented)

Every feature listed below is built, functional, and shipping in the current version.

---

## 5.1 Natural Language → AWS Infrastructure

Describe any architecture in plain English. The AI agent pipeline interprets requirements, selects AWS services, generates an interactive architecture graph, estimates cost, and produces deployment-ready boto3 configurations — all in a single request.

**Example prompts:**
- *"Deploy a REST API with EC2, RDS PostgreSQL, and an S3 bucket for media uploads"*
- *"Build a serverless data pipeline: S3 → Lambda → DynamoDB"*
- *"Set up a VPC with public and private subnets, NAT gateway, and an ALB in front of two EC2 instances"*

**How it works:**

```
User prompt
    │
    ▼
Intent Agent  →  extracts app_type, scale, latency, storage, constraints
    │
    ▼
Prompt Enrichment Agent  →  rewrites vague input into explicit AWS-service spec
    │
    ▼
Tool Agent  →  LLM calls 88 registered tools to select & configure services
    │              produces ArchitectureGraph + boto3 config dicts
    ▼
Cost Agent + Visual Agent  →  parallel: monthly cost estimate + React Flow layout
    │
    ▼
Architecture saved (versioned) → returned to frontend
```

---

## 5.2 AI Chat Editing

After initial generation, users refine the architecture conversationally:

- *"Add an ElastiCache Redis cluster between EC2 and RDS"*
- *"Remove the NAT gateway, I'll use a public subnet instead"*
- *"Change the RDS engine from MySQL to PostgreSQL"*

The **Edit Agent** modifies the existing graph, the **Cost Agent** re-estimates, and the **Visual Agent** re-layouts. Each edit creates a new architecture version; full history is preserved.

---

## 5.3 Visual Drag-and-Drop Builder

A React Flow canvas at `/drag-build` provides a fully visual alternative to chat:

- **88+ AWS service tiles** organized into 10 categories (Compute, Storage, Database, Networking, Security, Messaging, Analytics, DevOps, Monitoring, Application)
- **Searchable sidebar** with live filtering
- **Connection validation** — invalid edges (e.g., VPC-to-VPC) are blocked with an error toast; valid edges get auto-labeled ("reads/writes", "triggers", etc.)
- **Per-node configuration panel** — click any node to set instance type, engine, runtime, memory, etc.
- **Undo** support
- **Deterministic boto3 generation** — `_generate_boto3_config()` converts the canvas to deployment configs *without* calling the LLM

Both the chat path and the canvas path converge on the same deployment engine.

---

## 5.4 Interactive Architecture Viewer

Every project gets a React Flow diagram showing:

- Service nodes (colored per AWS category, with icons)
- Connection edges with labels
- Minimap, zoom, fullscreen toggle
- **"Code" tab** — view the raw boto3 configuration for each resource
- **Resource chips** — quick-scan list (capped at 8, with "Show All" modal for larger architectures)

---

## 5.5 One-Click Deployment (boto3 Engine)

The **Boto3 Executor** provisions real AWS resources directly via the AWS SDK — no Terraform, no CloudFormation intermediary.

**Execution pipeline:**
1. Placeholder resolution — `__PROJECT__`, `__REGION__`, `__RESOURCE_ID__` tokens replaced with real values
2. Name sanitization — per-service AWS naming rules enforced (S3 lowercase, RDS alphanumeric-hyphen, etc.)
3. EC2 key pair auto-creation — fresh `.pem` key generated for every EC2 instance
4. RDS auto-networking — if no VPC specified, executor auto-creates VPC + subnets + SG + DB subnet group
5. Resource creation — boto3 API call with resource ID extraction
6. Tagging — `CreatedBy: Infra-Agent`, `Project`, `ManagedBy`
7. Waiters — RDS `db_instance_available`, EC2 `instance_running`, etc.
8. LLM-assisted error repair — on failure, LLM attempts to fix params and retry once
9. State persistence — all resource IDs, ARNs, IPs, key material saved to `Deployment.resource_state_json`

**Live SSE log streaming** — every step streams `text/event-stream` events to a terminal-style log viewer in the browser.

---

## 5.6 Deployment Management

| Capability | Description |
|-----------|-------------|
| **Deploy** | One-click deploy of current architecture version |
| **Redeploy** | Re-deploy with confirmation dialog (creates new deployment record) |
| **Destroy All** | Dependency-ordered teardown of every resource in the project |
| **Destroy Single** | Remove a specific resource from a deployment |
| **Batch Destroy** | Select multiple resources and destroy them together |
| **Deployment History** | Full list of past deployments with status, timestamps, logs |

---

## 5.7 EC2 Connection Info

After an EC2 instance reaches `running`:

- **Download `.pem`** button — get the private key directly from the UI
- **Public IP / DNS** — shown as soon as available
- **SSH commands** — pre-built for Amazon Linux and Ubuntu, with copy buttons
- `chmod 400` reminder

---

## 5.8 AWS Resource Explorer

A standalone dashboard at `/aws-explorer` that discovers *all* AWS resources in an account — including those **not** created by Infra-Agent.

- Region selector (all real AWS regions fetched live)
- Discovers: EC2, S3, Lambda, RDS, ECS, DynamoDB, SQS, SNS, CloudFront, ElastiCache, API Gateway, App Runner, VPCs, Load Balancers
- Per-resource: ID, name, type/engine/runtime, state (color-coded), creation time
- **Search & filter** within results
- **Bulk delete** — select resources → confirm → delete via appropriate AWS API

---

## 5.9 Cost Estimation (Per Architecture)

Every architecture generation and edit triggers the **Cost Agent**, which estimates monthly AWS costs using static pricing heuristics with LLM fallback. The result is a per-service cost breakdown displayed in the Architecture tab.

---

## 5.10 Cost Analysis Dashboard

A cross-project cost intelligence page at `/cost-analysis` backed by the real **AWS Cost Explorer API**:

- **Total spend** across all projects with date range selection
- **Monthly trend chart**
- **Top-spending projects** ranked
- **Service-level breakdown**
- **Savings recommendations** — flags over-provisioned resources, suggests Reserved Instances, identifies idle resources
- **Cost forecast** — projected spend based on current trends
- **Comparator Agent** (UI) — side-by-side cloud provider comparison (AWS / GCP / Azure) for cost benchmarking

---

## 5.11 CloudWatch Monitoring

### Per-Project Monitoring Tab

Live metrics for deployed resources:

| Resource Type | Metrics |
|--------------|---------|
| **Lambda** | Invocations, errors, duration, throttles |
| **RDS** | CPU utilization, connections, free storage, read/write latency |
| **EC2** | CPU utilization, network in/out, status checks |

### Global Monitoring Dashboard (`/monitoring`)

Cross-project view: recent deployments, resource counts, failure trends.

---

## 5.12 Authentication & Security

| Feature | Implementation |
|---------|---------------|
| **JWT Auth** | Register → login → JWT access token (60 min expiry) |
| **Password Storage** | bcrypt hashed, never stored in plain text |
| **AWS Credentials** | AES-encrypted at rest in the database |
| **LLM API Key** | AES-encrypted at rest in the database |
| **Per-User Isolation** | Each user sees only their own projects, credentials, and deployments |

---

## 5.13 Configurable LLM Provider

Infra-Agent is **LLM-agnostic**. Users configure their own provider in Settings:

- **Base URL** — any OpenAI-compatible endpoint (OpenAI, Azure OpenAI, Anthropic via proxy, Ollama, vLLM, LiteLLM, etc.)
- **API Key** — stored encrypted
- **Model Name** — user-selectable (gpt-4o, gpt-4-turbo, claude-3, llama-3, deepseek, etc.)

---

## 5.14 User Preferences

Configurable defaults persisted per user:

- **Default AWS Region**
- **Naming Convention** — `project-resource`, `env-project-resource`, or `kebab-case`
- **Default VPC** toggle — use account's default VPC vs. create new

---

## 5.15 API Request Logging

Every API request/response is logged to a daily CSV file (`logs/api_requests_YYYY-MM-DD.csv`). Viewable from the `/logs` page with date picker.

---

## 5.16 Chat History

Full conversation history is persisted per project. Users can scroll back through their architecture generation and editing prompts.

---

## 5.17 Architecture Versioning

Every generation or edit creates a new `Architecture` record linked to the project. Users can view the full evolution of their infrastructure design.

---

# 6. AI Agent Architecture

Seven specialized agents, each stateless with a single `async run()` method. System prompts are stored as Markdown files in `backend/app/prompts/`.

| # | Agent | Purpose | Input → Output |
|---|-------|---------|----------------|
| 1 | **Intent Agent** | Parse natural language into structured requirements | NL string → `IntentOutput` (app_type, scale, latency, storage, realtime, constraints) |
| 2 | **Prompt Enrichment Agent** | Rewrite vague prompts into detailed AWS specs | Raw prompt → enriched prompt with explicit service names |
| 3 | **Tool Agent** | Orchestrate LLM tool-calling to design architecture | `IntentOutput` + prompt → `ArchitectureGraph` + boto3 configs |
| 4 | **Architecture Agent** | Design graph from structured intent (legacy flow) | `IntentOutput` → `ArchitectureGraph` |
| 5 | **Edit Agent** | Modify existing architecture via conversation | Graph + NL modification → modified Graph |
| 6 | **Cost Agent** | Estimate monthly AWS costs | `ArchitectureGraph` → per-service cost breakdown |
| 7 | **Visual Agent** | Generate React Flow layout | `ArchitectureGraph` → positioned + styled node/edge JSON |

### Tool Registry

The `ToolRegistry` auto-discovers **88 tool classes** across 10 AWS service packages + 1 utility:

| Category | Count | Examples |
|----------|-------|---------|
| Compute | 10 | EC2, Lambda, ECS/Fargate, EKS, App Runner, Elastic Beanstalk, Batch, Lightsail |
| Networking | 14 | VPC, Subnet, Security Group, ALB/ELB, API Gateway, Route53, CloudFront, NAT Gateway |
| Storage | 7 | S3, EBS, EFS, FSx, Backup, Glacier, Storage Gateway |
| Databases | 11 | RDS, Aurora, DynamoDB, ElastiCache, Redshift, Neptune, DocumentDB, Keyspaces, Timestream |
| Security | 8 | IAM, Cognito, Secrets Manager, KMS, WAF, Shield, ACM, GuardDuty |
| Messaging | 9 | SQS, SNS, EventBridge, Kinesis, Step Functions, MQ, AppSync |
| Monitoring | 6 | CloudWatch Alarm, Log Group, CloudTrail, Config Rule, X-Ray, Health Event |
| DevOps | 8 | CloudFormation, SSM Parameter, CodePipeline, CodeBuild, CodeCommit, CodeDeploy, ECR, CodeArtifact |
| Analytics | 8 | Athena, Glue, EMR, SageMaker, QuickSight, Lake Formation, MSK, OpenSearch |
| Application | 7 | SES, Pinpoint, Amplify, MediaConvert, Location, IoT, Connect |
| Utility | 1 | ConnectServices (edge creation) |

Each tool exposes a JSON schema (shown to the LLM) and an `execute(params)` method that returns a boto3 config dict.

---

# 7. Technical Architecture

## 7.1 System Overview

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  React 19 · TypeScript 5.9 · Vite 7 · Tailwind  │
│  React Flow (@xyflow/react) · Framer Motion     │
│  Axios · React Router · Lucide Icons            │
└──────────────────────┬──────────────────────────┘
                       │  REST + SSE + WebSocket
                       ▼
┌─────────────────────────────────────────────────┐
│                   Backend                        │
│  FastAPI · Uvicorn · Python 3.12+               │
│  SQLAlchemy (async) · aiosqlite · Alembic       │
│  python-jose (JWT) · passlib (bcrypt)           │
│  boto3 · OpenAI SDK · httpx · structlog         │
│  Celery + Redis (task queue)                    │
└──────────┬────────────────────┬─────────────────┘
           │                    │
           ▼                    ▼
┌──────────────────┐  ┌──────────────────────────┐
│   SQLite (DB)    │  │   AWS (boto3 direct)     │
│  Users, Projects │  │  EC2, RDS, S3, Lambda…   │
│  Architectures   │  │  CloudWatch, Cost Explorer│
│  Deployments     │  │  Resource Explorer        │
│  Chat Messages   │  └──────────────────────────┘
└──────────────────┘
```

## 7.2 Database Schema

| Table | Key Fields |
|-------|-----------|
| **users** | id, email, hashed_password, aws_credentials_encrypted, preferences (JSON), llm_api_key_encrypted, llm_preferences (JSON) |
| **projects** | id, user_id (FK), name, description, status, region, natural_language_input, source (`ai_generated` / `drag_built`) |
| **architectures** | id, project_id (FK), version, intent_json, graph_json, terraform_files_json (boto3 configs), cost_json, visual_json |
| **deployments** | id, project_id (FK), architecture_version, action, status, logs, error_message, error_details, resource_state_json |
| **chat_messages** | id, project_id (FK), role, content, architecture_version |

## 7.3 API Surface

**45 endpoints** across 10 route groups:

| Group | Prefix | Endpoints | Purpose |
|-------|--------|-----------|---------|
| Auth | `/auth` | 3 | Register, login, profile |
| Projects | `/projects` | 4 | CRUD projects |
| Architecture | `/projects/{id}` | 5 | Generate, edit, get architecture/cost/messages |
| Deployment | `/projects/{id}` | 10 | Deploy, redeploy, destroy, status, history, EC2 keys |
| Monitoring | `/projects/{id}` | 1 | CloudWatch metrics |
| WebSocket | `/projects/{id}/logs` | 1 | Real-time log streaming |
| Config | `/config` | 9 | Preferences, AWS creds, LLM config |
| Cost Analysis | `/cost-analysis` | 4 | Summary, forecast, recommendations, services |
| Logs | `/logs` | 2 | Request log dates + log viewer |
| Drag Build | `/drag-build` | 2 | Save/update canvas projects |
| AWS Explorer | `/aws` | 3 | Regions, resources, delete |

---

# 8. User Flow

```
Register / Login
       │
       ▼
Settings  ◄── configure AWS credentials + LLM API key (required first)
       │
       ▼
  Dashboard
       │
       ├──► New Project (Chat)
       │      │
       │      ├── Describe architecture in English
       │      ├── AI generates graph + cost estimate
       │      ├── Refine with follow-up messages
       │      ├── Review interactive diagram + code
       │      ├── Click Deploy → live SSE logs
       │      ├── Download .pem → SSH into EC2
       │      └── Monitor metrics / Destroy
       │
       ├──► New Project (Drag & Drop)
       │      │
       │      ├── Drag AWS tiles onto canvas
       │      ├── Draw connections, configure nodes
       │      ├── Save → boto3 config auto-generated
       │      ├── Deploy → same engine as chat path
       │      └── Monitor / Destroy
       │
       ├──► AWS Explorer — discover + delete any resource in the account
       ├──► Cost Analysis — spend trends, forecasts, savings recommendations
       ├──► Monitoring — cross-project CloudWatch metrics
       ├──► Deployments — global deployment history
       └──► Logs — API request audit trail
```

---

# 9. Competitive Positioning

| Platform | Approach | Limitation | Infra-Agent Advantage |
|----------|----------|------------|----------------------|
| **Terraform / OpenTofu** | Declarative IaC (HCL) | Steep learning curve; no visual builder; no AI | NL + visual; zero HCL knowledge needed |
| **Pulumi** | Imperative IaC (code) | Requires programming skill; no chat interface | Chat-first; code generated automatically |
| **AWS CDK** | TypeScript/Python abstractions | Still requires deep AWS knowledge | AI handles service selection + config |
| **Railway / Render** | PaaS — push code, get infra | Limited to supported stacks; no VPC/RDS control | Full AWS service catalog; fine-grained control |
| **Copilot for CLI** | AI-assisted terminal | Generates commands, doesn't execute or track state | End-to-end: generate → deploy → monitor → destroy |
| **Spacelift / Env0** | IaC automation/CI | Wraps Terraform; requires existing IaC codebase | Generates infra from scratch; no IaC prerequisite |

**Infra-Agent's moat:** The only tool that combines NL→infra generation, visual canvas, direct boto3 deployment, live monitoring, and cost analysis in a single product — purpose-built for developers who want to move fast without learning IaC.

---

# 10. Security Architecture

| Layer | Measure |
|-------|---------|
| **Authentication** | JWT tokens (HS256, 60-min expiry); bcrypt password hashing |
| **Credential Storage** | AES encryption for AWS creds + LLM API keys at rest |
| **User Isolation** | All queries scoped to `current_user.id`; no cross-user data access |
| **AWS Interaction** | User's own AWS credentials used; Infra-Agent never stores AWS resources in its own account |
| **API Key Masking** | LLM API keys returned as `sk-...XXXX` (last 4 chars only) |
| **Request Logging** | Every API call logged with timestamp, method, path, status, duration |
| **Input Validation** | Pydantic schemas on all endpoints; boto3 parameter sanitization before AWS calls |

---

# 11. Key Metrics

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| **Time to First Deploy** | Seconds from first prompt to running AWS resources | < 5 minutes |
| **Deployment Success Rate** | % of deploys that complete without manual intervention | > 90% |
| **Active Projects per User** | Adoption depth | > 3 |
| **Cost Estimation Accuracy** | Estimated vs. actual AWS spend deviation | < 20% |
| **NL→Architecture Accuracy** | Does the AI pick the right services for the prompt? | > 85% first-try satisfaction |
| **Teardown Completeness** | % of resources successfully destroyed on "Destroy All" | 100% (no orphans) |

---

# 12. Product Roadmap

### Phase 1 — Foundation (Completed ✅)

- [x] NL → AWS architecture generation (7-agent pipeline)
- [x] 88 AWS service tools across 10 categories
- [x] Interactive React Flow architecture viewer
- [x] Direct boto3 deployment engine with SSE streaming
- [x] Dependency-ordered destroy (full + single + batch)
- [x] EC2 key pair automation + SSH connection info
- [x] Visual drag-and-drop builder (50+ service tiles)
- [x] AWS Resource Explorer (multi-region, multi-service)
- [x] CloudWatch monitoring (per-project + global)
- [x] Cost estimation (static pricing + LLM hybrid)
- [x] AWS Cost Explorer integration (summary, forecast, recommendations)
- [x] JWT auth + encrypted credential storage
- [x] LLM-agnostic provider support
- [x] Chat history + architecture versioning
- [x] API request logging

### Phase 2 — Reliability & Polish (In Progress 🔄)

- [ ] Deployment error recovery — smarter LLM repair, subnet CIDR conflict resolution, SG ID resolution
- [ ] Pre-deploy validation — catch misconfigured resources before hitting AWS
- [ ] Architecture templates — one-click starter architectures (3-tier web app, serverless API, data pipeline)
- [ ] Import existing infra — import from AWS account into an Infra-Agent project
- [ ] Terraform/CloudFormation export — generate IaC files from architecture graph
- [ ] Notification system — deployment success/failure alerts

### Phase 3 — Intelligence (Planned 📋)

- [ ] Autonomous Cost Optimization Agent — continuously right-size running resources
- [ ] Smart Scaling Agent — predictive autoscaling based on traffic patterns
- [ ] Monitoring Agent — automated anomaly detection + alerting
- [ ] Multi-cloud cost comparison — real pricing comparison across AWS / GCP / Azure
- [ ] Architecture recommendation engine — suggest improvements based on usage patterns

### Phase 4 — Multi-Cloud & Enterprise (Future 🔮)

- [ ] GCP deployment support
- [ ] Azure deployment support
- [ ] Infrastructure migration (AWS ↔ GCP ↔ Azure)
- [ ] Team workspaces + RBAC (role-based access control)
- [ ] SSO / SAML authentication
- [ ] Audit trail (compliance-grade)
- [ ] Self-healing infrastructure — auto-remediate failed resources
- [ ] Predictive scaling — ML-driven capacity planning
- [ ] API / SDK for programmatic access

---

# 13. Startup Alignment

### Why This Matters for Startups

| Startup Reality | How Infra-Agent Helps |
|----------------|----------------------|
| Can't afford a DevOps hire | Any developer can deploy production infra via chat |
| Need to ship fast, iterate daily | New architecture in seconds; redeploy in one click |
| AWS bill anxiety | Cost estimation before deploy; savings recommendations after |
| Throwaway environments | One-click teardown — no orphaned resources, no surprise bills |
| Technical co-founder doing everything | Single tool: design + deploy + monitor + tear down |
| Hackathon / demo day pressure | Working infra in under 5 minutes from a single prompt |
| Investor demos | Professional architecture diagrams auto-generated |
| Pivoting frequently | Destroy old infra, generate new architecture, deploy — all in the same session |

### Go-to-Market

| Channel | Strategy |
|---------|----------|
| **Developer communities** | Demos on Twitter/X, Reddit (r/aws, r/devops, r/SaaS), Hacker News |
| **Hackathons** | Sponsor prizes; show 5-minute deploy workflow |
| **YouTube / tutorials** | "Deploy a full-stack app to AWS in 3 minutes" content |
| **Product Hunt** | Launch with demo video + free tier |
| **Startup programs** | Integrate with AWS Activate, Y Combinator Startup School |
| **Open source** | Core engine open source → paid cloud-hosted version |

### Pricing Model (Proposed)

| Tier | Price | Includes |
|------|-------|---------|
| **Free** | $0 | 3 projects, 10 deploys/month, community support |
| **Pro** | $29/mo | Unlimited projects, unlimited deploys, priority LLM routing, architecture templates |
| **Team** | $79/mo per seat | Everything in Pro + shared workspaces, RBAC, audit logs, SSO |
| **Enterprise** | Custom | On-prem deployment, dedicated support, SLA, compliance certifications |

*Note: Users bring their own AWS credentials and LLM API key. Infra-Agent never provisions resources in its own account — the user pays AWS directly.*

---

# 14. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| AWS API errors during deployment | Failed deploys, partial resource creation | LLM-assisted repair + rollback; state tracking ensures no orphans |
| LLM generates incorrect architecture | Wrong services deployed; wasted cost | Intent Agent validates requirements; Cost Agent flags anomalies; user reviews graph before deploy |
| Cost estimation inaccuracy | User surprised by AWS bill | Cross-reference with AWS Pricing API; post-deploy cost tracking via Cost Explorer |
| Rate limits on AWS APIs | Deployment failures during high concurrency | Exponential backoff; per-user request queuing via Celery + Redis |
| Security — credential exposure | User AWS keys or LLM keys leaked | AES encryption at rest; API key masking on read; HTTPS in production |
| LLM provider downtime | Architecture generation unavailable | Fallback to Architecture Agent (non-tool-calling path); user can switch providers |
| Single-cloud lock-in (AWS only) | Limits addressable market | Phase 4 roadmap adds GCP + Azure; architecture abstraction layer in design |

---

# 15. Success Criteria (6-Month Milestones)

| Milestone | Target |
|-----------|--------|
| Registered users | 500+ |
| Projects created | 2,000+ |
| Successful deployments | 5,000+ |
| Deployment success rate | > 92% |
| Average time to first deploy | < 4 minutes |
| GitHub stars (if open-sourced) | 1,000+ |
| Paying customers (Pro tier) | 50+ |

---

*Infra-Agent — Talk to your infrastructure. Deploy it in one click.*
