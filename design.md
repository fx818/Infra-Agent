# Infra-Agent — User Workflow & Design Guide

> A step-by-step walkthrough of the application from the perspective of a first-time user: how to access it, navigate it, build infrastructure, and manage cloud resources.

---

## Table of Contents

1. [Overview of the User Journey](#overview-of-the-user-journey)
2. [Step 1 — Accessing the App](#step-1--accessing-the-app)
3. [Step 2 — Registration](#step-2--registration)
4. [Step 3 — First-Time Settings (Critical)](#step-3--first-time-settings-critical)
5. [Step 4 — The Dashboard](#step-4--the-dashboard)
6. [Path A — Build with AI Chat](#path-a--build-with-ai-chat)
   - [4A.1 Create a Project](#4a1-create-a-project)
   - [4A.2 Describe Your Architecture](#4a2-describe-your-architecture)
   - [4A.3 Review the Generated Architecture](#4a3-review-the-generated-architecture)
   - [4A.4 Refine with Follow-up Chat](#4a4-refine-with-follow-up-chat)
   - [4A.5 Deploy to AWS](#4a5-deploy-to-aws)
   - [4A.6 EC2 SSH Access](#4a6-ec2-ssh-access)
   - [4A.7 Monitor Your Resources](#4a7-monitor-your-resources)
   - [4A.8 Destroy Resources](#4a8-destroy-resources)
7. [Path B — Build with Drag and Drop](#path-b--build-with-drag-and-drop)
   - [4B.1 Open the Canvas](#4b1-open-the-canvas)
   - [4B.2 Add AWS Services](#4b2-add-aws-services)
   - [4B.3 Connect Services](#4b3-connect-services)
   - [4B.4 Configure Each Node](#4b4-configure-each-node)
   - [4B.5 Save the Project](#4b5-save-the-project)
   - [4B.6 Deploy to AWS](#4b6-deploy-to-aws)
   - [4B.7 Edit the Canvas Later](#4b7-edit-the-canvas-later)
8. [AWS Explorer — Discover All Resources](#aws-explorer--discover-all-resources)
9. [Cost Analysis Dashboard](#cost-analysis-dashboard)
10. [Monitoring Dashboard](#monitoring-dashboard)
11. [Logs Viewer](#logs-viewer)
12. [Settings Reference](#settings-reference)
13. [Navigation Map](#navigation-map)
14. [Common User Scenarios](#common-user-scenarios)

---

## Overview of the User Journey

```
Open App
    │
    ├─► Register / Login
    │
    └─► Settings (add AWS credentials + LLM key)  ◄── MUST DO FIRST
            │
            ▼
        Dashboard  ◄────────────────────────────────────────┐
            │                                               │
            ├─► [New Project] ── AI Chat ──► Architecture  │
            │              │                 │             │
            │              │                 └─► Deploy ───┤
            │              │                               │
            │              └─► Drag & Drop ──► Save ──► Deploy
            │
            ├─► AWS Explorer  (discover + delete existing resources)
            ├─► Cost Analysis (cross-project cost dashboard)
            ├─► Monitoring    (global CloudWatch dashboard)
            ├─► Deployments   (all deployment history)
            └─► Logs          (API request logs)
```

---

## Step 1 — Accessing the App

Open your browser and navigate to:

```
http://localhost:5173       (development, after running npm run dev)
```

You will land on the **Login page**. If you have not registered yet, click **"Register"** or **"Create account"** at the bottom of the form.

---

## Step 2 — Registration

Fill in the registration form:

| Field | Notes |
|---|---|
| **Email** | Used as your unique login identifier |
| **Password** | Stored as a bcrypt hash — never stored in plain text |

Click **Register**. You are automatically logged in and redirected to the **Dashboard**.

> A JWT access token is issued and stored in your browser's local storage. It expires after 60 minutes, after which you will be prompted to log in again.

---

## Step 3 — First-Time Settings (Critical)

Before you can generate any architecture or deploy anything, you must configure your credentials.

Click the **Settings** link in the left sidebar (gear icon at the bottom).

### 3.1 — AWS Credentials

Under the **AWS Credentials** section:

| Field | Where to find it |
|---|---|
| **AWS Access Key ID** | AWS Console → IAM → Users → Security Credentials |
| **AWS Secret Access Key** | Same as above (shown once at creation) |
| **Default Region** | e.g. `us-east-1`, `ap-south-1`, `eu-west-1` |

Click **Save AWS Credentials**. These are encrypted with AES and stored in the database — they are never stored in plain text.

### 3.2 — LLM / AI Configuration

Under the **AI Configuration** section:

| Field | What to enter |
|---|---|
| **API Key** | Your OpenAI API key (starts with `sk-`) or your provider's key |
| **Model** | e.g. `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo` |
| **Base URL** | `https://api.openai.com/v1` (default) — change only if using Azure, Ollama, etc. |

Click **Save LLM Settings**.

> Without valid LLM credentials, the AI chat path will fail. Without valid AWS credentials, deployment will fail. Both are required for the full experience.

### 3.3 — Naming Convention

Optionally set a **resource naming convention** (e.g. `kebab-case`, `snake_case`). This affects how resource names are auto-generated from your project name. Leave as default if unsure.

---

## Step 4 — The Dashboard

After setup, click **Dashboard** in the sidebar. You see an overview of all your projects.

```
┌─────────────────────────────────────────────────────────┐
│  Infra-Agent                          [+ New Project]   │
│─────────────────────────────────────────────────────────│
│  My Web App          ● deployed    AI   us-east-1       │
│  DynamoDB API        ● ready       AI   us-east-1       │
│  Test Canvas         ● deployed  Drag   eu-west-1       │
│  Batch Pipeline      ○ creating   AI   us-west-2        │
└─────────────────────────────────────────────────────────┘
```

Each project card shows:
- **Name** — what you called the project
- **Status badge** — `created`, `generating`, `ready`, `deploying`, `deployed`, `failed`
- **Source** — `AI` (generated via chat) or `Drag` (drag-and-drop canvas)
- **Region** — the AWS region it targets

You can filter by status or source type using the filter controls at the top.

---

## Path A — Build with AI Chat

This path lets you describe any AWS architecture in natural language and have the AI design and deploy it for you.

---

### 4A.1 Create a Project

From the Dashboard, click **+ New Project**.

Fill in:
- **Project Name** — e.g. `my-rest-api` (used to generate resource names in AWS)
- **Description** — optional, helps the AI understand context
- **AWS Region** — select the region where resources will be deployed

Click **Create Project**. You are taken to the project detail page.

---

### 4A.2 Describe Your Architecture

You land on the **Architecture tab** of the project.

In the chat input at the bottom, describe what you want to build in plain English. Be as specific or as vague as you like. Examples:

```
"Build a scalable REST API with EC2, an Application Load Balancer, and RDS PostgreSQL"

"I need a serverless data pipeline: API Gateway → Lambda → DynamoDB with SQS as a buffer"

"Create a 3-tier web application: React frontend on S3+CloudFront, Node.js on EC2,
 PostgreSQL on RDS, with a VPC separating public and private subnets"

"Simple Lambda function triggered by SQS with a DynamoDB table"
```

Press **Enter** or click the **Generate** button.

The system shows a typing indicator while the AI pipeline runs (usually 10–30 seconds depending on complexity).

---

### 4A.3 Review the Generated Architecture

Once generation completes, you see:

#### Architecture Graph (Visual Tab)

An interactive React Flow diagram appears showing:
- **Nodes** — each AWS service as a colored tile with its logo and label
- **Edges** — labeled arrows showing data flow / relationships (e.g. "triggers", "stores data", "routes to")
- **Controls** — zoom in/out, fit to screen, fullscreen mode, minimap

You can drag nodes around to rearrange the layout if you wish (read-only by default in architecture view).

#### Cost Estimate Panel

Below the graph (or in a side panel) you see a per-service cost breakdown:

```
Estimated Monthly Cost
─────────────────────
EC2 (t3.medium)          $  33.00
RDS PostgreSQL (db.t3)   $  55.00
Application LB           $  22.00
Route 53                 $   0.50
                         ─────────
Total                    $ 110.50 / month
```

> This is an AI estimate — actual costs depend on usage. Use AWS Cost Explorer for exact billing.

#### Code Tab

Switch to the **Code** tab to see the raw boto3 configuration JSON — the exact API calls that will be made when you deploy. This is useful for debugging or understanding what the AI designed.

---

### 4A.4 Refine with Follow-up Chat

Don't like part of the design? Type a follow-up in the same chat input:

```
"Replace the EC2 instances with ECS Fargate containers"
"Add an ElastiCache Redis cluster between the app and the database"
"Remove Route 53, I'll manage DNS myself"
"Make the RDS instance Multi-AZ"
```

The **Edit Agent** modifies the existing graph, then the system regenerates the cost estimate and visual layout. The previous version is preserved — architecture history is never deleted.

---

### 4A.5 Deploy to AWS

When you are happy with the architecture, click the **Deployment** tab.

Click the green **Deploy** button.

The deployment log panel opens and streams real-time output:

```
[12:04:01] Starting deployment for project: my-rest-api
[12:04:01] Creating VPC...
[12:04:03] ✓ VPC created: vpc-0a1b2c3d
[12:04:03] Creating Subnet (public)...
[12:04:05] ✓ Subnet created: subnet-0x9y8z
[12:04:05] Creating Security Group...
[12:04:06] ✓ Security Group created: sg-0abc1234
[12:04:06] Creating EC2 Key Pair: my-rest-api-keypair ...
[12:04:07] ✓ Key pair created
[12:04:07] Launching EC2 instance (t3.medium)...
[12:04:22] ✓ EC2 instance running: i-0a1b2c3d4e5f
[12:04:22]   Public IP: 54.23.101.45
[12:04:22]   Public DNS: ec2-54-23-101-45.compute-1.amazonaws.com
[12:04:22] Creating RDS PostgreSQL instance...
[12:06:45] ✓ RDS instance available: my-rest-api-db
[12:06:45] Creating Application Load Balancer...
[12:07:01] ✓ Load balancer active: arn:aws:elasticloadbalancing:...
[12:07:01] ─────────────────────────────────────────────
[12:07:01] Deployment complete. 6/6 resources created.
```

> Deployment can take 1–15 minutes depending on services (RDS and EKS clusters take the longest).

The project status on the Dashboard updates to **deployed**.

---

### 4A.6 EC2 SSH Access

If your architecture includes EC2 instances, the **EC2 Connection Info** panel appears in the Deployment tab after deployment:

```
┌─────────────────────────────────────────────────────┐
│  EC2 Connection Info                                │
│─────────────────────────────────────────────────────│
│  Key Pair:   my-rest-api-keypair  [Download .pem]  │
│  Public IP:  54.23.101.45                           │
│                                                     │
│  SSH (Amazon Linux):                                │
│  chmod 400 my-rest-api-keypair.pem                  │
│  ssh -i my-rest-api-keypair.pem ec2-user@54.23.101.45│
│                                                     │
│  SSH (Ubuntu):                                      │
│  ssh -i my-rest-api-keypair.pem ubuntu@54.23.101.45 │
└─────────────────────────────────────────────────────┘
```

Click **Download .pem** to save the private key file. Run `chmod 400` on it before using it.

> The PEM file is generated fresh every time you deploy. It is stored in the deployment record and only accessible through this UI.

---

### 4A.7 Monitor Your Resources

Click the **Monitoring** tab within the project.

You see live CloudWatch metrics for deployed resources:

- **Lambda**: invocation count, error count, average duration (ms), throttles
- **RDS**: CPU utilization (%), DB connections, free storage (GB), read/write latency
- **EC2**: CPU utilization

Charts auto-refresh every 30 seconds.

---

### 4A.8 Destroy Resources

To tear down all resources created for this project, click the **Deployment** tab and click the red **Destroy** button.

The system reads the stored resource state and deletes every resource in reverse dependency order, streaming a destruction log just like deployment. All AWS resources are deleted from your account.

> The project record and chat history are kept in the local database. You can re-deploy at any time.

---

## Path B — Build with Drag and Drop

This path is for users who prefer a visual, no-code approach to designing infrastructure. No AI is needed — you drag service tiles, draw connections, and save.

---

### 4B.1 Open the Canvas

Click **Drag & Drop Builder** in the left sidebar (or navigate to `/drag-build`).

You see a split-panel view:
- **Left panel** — AWS service catalog (categorized list of all available services)
- **Right panel** — React Flow canvas (empty white workspace)

---

### 4B.2 Add AWS Services

In the left sidebar, browse the categories:

```
Compute      → EC2, Lambda, ECS, EKS, App Runner, Fargate…
Storage      → S3, EBS
Database     → RDS, DynamoDB, ElastiCache, Redshift
Networking   → VPC, Subnet, Security Group, ALB, CloudFront…
Security     → IAM, Cognito, Secrets Manager, WAF…
Messaging    → SQS, SNS, Kinesis, EventBridge
Monitoring   → CloudWatch
DevOps       → ECR, CloudFormation
```

Use the **search bar** at the top of the sidebar to find a service by name.

**Drag** any service tile and **drop** it onto the canvas. A node appears with the service's logo and name.

Add as many services as your architecture needs.

---

### 4B.3 Connect Services

To link two services:

1. Hover over the **source node** — connection handles (small dots) appear on the edges
2. Click and drag from a handle to the **target node**
3. The connection is validated automatically:
   - ✅ If the connection makes sense (e.g. Lambda → DynamoDB), an edge is drawn with a label like "reads/writes"
   - ❌ If the connection is invalid (e.g. two VPCs connected directly), an error toast appears and the edge is rejected

---

### 4B.4 Configure Each Node

Click any node on the canvas to open its **property panel** on the right side:

**Example — EC2 Node:**
```
Instance Type:   [ t3.micro ▼ ]
AMI:             [ Amazon Linux 2023 ▼ ]
Storage (GB):    [ 20 ]
```

**Example — RDS Node:**
```
Engine:          [ PostgreSQL ▼ ]
Instance Class:  [ db.t3.micro ▼ ]
Storage (GB):    [ 20 ]
Multi-AZ:        [ ☐ ]
```

**Example — Lambda Node:**
```
Runtime:         [ Python 3.12 ▼ ]
Memory (MB):     [ 128 ]
Timeout (s):     [ 30 ]
```

Adjust defaults as needed. Every property maps directly to a boto3 API parameter.

---

### 4B.5 Save the Project

Once your canvas is ready:

1. Click **Save Project** (top right of the canvas)
2. Enter a **Project Name** (e.g. `my-canvas-app`)
3. Select the **AWS Region**
4. Click **Save**

The canvas is serialized and sent to the backend. The system deterministically converts each node into boto3 API call configurations — no LLM is involved. The project appears on the Dashboard with source badge **Drag**.

---

### 4B.6 Deploy to AWS

From the Dashboard, click on your drag-built project to open it.

Navigate to the **Deployment** tab and click **Deploy**. The same SSE streaming log you saw in Path A appears. The deployment engine processes each service in dependency order.

---

### 4B.7 Edit the Canvas Later

To add or remove services after saving:

1. From the Dashboard, click the project
2. Click **Edit Canvas** (or navigate to `/drag-build?projectId=YOUR_ID`)
3. The canvas reopens with your saved nodes and edges
4. Add new nodes, delete unwanted ones, redraw connections
5. Click **Update Project** to save the new version

Alternatively, you can edit a drag-built project using the **AI chat** in the Architecture tab:

```
"Add a CloudFront distribution in front of the S3 bucket"
"Add an SQS queue between the API Gateway and Lambda"
```

The Edit Agent modifies the architecture graph and the system regenerates deployment configs deterministically (not via LLM tool calls) to ensure every node is properly configured.

---

## AWS Explorer — Discover All Resources

Click **AWS Explorer** in the sidebar.

This page shows **all AWS resources in your account** — including ones that were NOT created by Infra-Agent.

### How to Use

1. Select a **region** from the dropdown (all regions are fetched live)
2. Click **Fetch Resources** → the system queries EC2, S3, Lambda, RDS, ECS, DynamoDB, SQS, SNS, CloudFront, ElastiCache, API Gateway, App Runner, VPCs, and Load Balancers
3. Browse the results — each resource shows:
   - Resource name / ID
   - Service type and sub-type (e.g. engine for RDS, runtime for Lambda)
   - **State** — color-coded (green = running/active, yellow = pending/building, red = stopped/failed)
   - Creation date
4. Use the **search bar** to filter by name, type, or ID

### Bulk Delete

Check the checkbox next to any resources you want to remove, then click **Delete Selected**. A confirmation dialog appears. Confirmed deletions are processed via the appropriate AWS delete API.

> Be careful — deletions are permanent and cannot be undone from within this app.

---

## Cost Analysis Dashboard

Click **Cost Analysis** in the sidebar.

This page gives you a consolidated view of estimated infrastructure costs across all your projects:

```
Total Estimated Monthly Cost: $342.50

Top Spenders
─────────────────────────────────────
1. prod-web-app        $142.00  ████████████
2. data-pipeline       $ 98.00  ████████
3. analytics-stack     $ 67.50  █████
4. dev-scratch         $ 35.00  ███

Monthly Trend
Jan: $210   Feb: $285   Mar: $342  (projected)

Savings Recommendations
• prod-web-app: EC2 t3.large instance runs at 8% average CPU — consider t3.small ($22/mo savings)
• data-pipeline: RDS instance idle 60% of time — consider Aurora Serverless
```

> All cost figures are AI estimates based on service types and approximate usage. Not a substitute for the AWS Cost Explorer.

---

## Monitoring Dashboard

Click **Monitoring** in the sidebar (global view).

This page shows an aggregate view across all deployed projects:

- Total deployed projects and resource count
- Recent deployment events (success / failure timeline)
- Quick links to per-project monitoring

For detailed per-resource metrics (CPU graphs, invocation counts, latency charts), open a specific project and click its **Monitoring** tab.

---

## Logs Viewer

Click **Logs** in the sidebar.

Every API request made to the backend is logged to a daily CSV file. The Logs page lets you browse these files:

1. Select a **date** from the available log files
2. Browse the table: timestamp, method, path, status code, duration (ms), request/response body excerpt
3. Use the search to filter by path or status code

This is useful for debugging deployment issues or understanding what API calls were made.

---

## Settings Reference

Click **Settings** (gear icon in the sidebar).

| Section | Fields | Purpose |
|---|---|---|
| **AWS Credentials** | Access Key ID, Secret Access Key, Default Region | Used by boto3 for all AWS operations |
| **AI Configuration** | API Key, Model, Base URL | Used by all 6 AI agents |
| **Naming Convention** | Naming style preference | Controls how resource names are auto-generated |
| **Account** | Email, Password change | User account management |

All sensitive values (AWS keys, LLM API key) are encrypted before being stored in the database using AES symmetric encryption. The encryption key is set in the server's `.env` file and never leaves the server.

---

## Navigation Map

```
Sidebar Links
├── 🏠  Dashboard         /                     All projects
├── ➕  New Project       /projects/new          Create AI project
├── 🎨  Drag & Drop       /drag-build            Canvas builder
├── 🌐  AWS Explorer      /aws-explorer          Discover all AWS resources
├── 📊  Cost Analysis     /cost-analysis         Cross-project cost view
├── 📈  Monitoring        /monitoring            Global CloudWatch view
├── 🚀  Deployments       /deployments           All deployment history
├── 📋  Logs              /logs                  API request CSV logs
└── ⚙️  Settings          /settings              Credentials + preferences

Project Pages (reached from Dashboard → click a project)
└── /projects/:id
     ├── Architecture Tab   Chat, graph, code view, cost estimate
     ├── Deployment Tab     Deploy/Destroy, SSE logs, EC2 connection info
     └── Monitoring Tab     Per-resource CloudWatch metrics
```

---

## Common User Scenarios

### "I want to try the app for the first time"
1. Register → Settings → add AWS credentials + LLM key
2. Dashboard → New Project → name it `hello-world` → region `us-east-1`
3. Type: `"Create a simple S3 bucket and a Lambda function that reads from it"`
4. Review the graph and cost estimate
5. Click Deploy → watch the logs
6. When done, click Destroy to clean up

### "I want to deploy a full web application stack"
1. New Project → name `my-app`
2. Type: `"3-tier web app: ALB → EC2 (t3.medium) → RDS PostgreSQL, all in a VPC with public and private subnets"`
3. Review graph — check the VPC + subnet + security group nodes are present
4. If you want Redis caching: type `"Add ElastiCache Redis between EC2 and RDS"`
5. Deploy → download EC2 PEM → SSH in and deploy your app code

### "I want to visually design without typing"
1. Click Drag & Drop in sidebar
2. Drag VPC, Subnet, Security Group, EC2, RDS onto canvas
3. Connect EC2 → RDS
4. Click EC2 node → set instance type to `t3.medium`
5. Click RDS node → set engine to `postgresql`, class to `db.t3.micro`
6. Save Project → give it a name → go to project → Deploy

### "I have existing AWS resources I want to see"
1. Click AWS Explorer
2. Select region
3. Click Fetch Resources
4. Browse everything in your account across all service types

### "I want to check if my deployed resources are healthy"
1. Click a deployed project on the Dashboard
2. Go to Monitoring tab
3. See CPU/invocation/latency graphs for Lambda and RDS resources

### "I want to understand what the AI designed"
1. Open any project → Architecture tab
2. Click the **Code** tab (next to the graph view)
3. See the raw boto3 configs — every service call with its exact parameters

### "My deployment failed — how do I debug?"
1. Open the project → Deployment tab
2. Scroll through the SSE log to find the `✗` error line
3. The error message from AWS is shown inline
4. Go to Settings → Logs → open today's log file for the full request/response trace
5. Fix the issue (usually by editing the architecture to remove an unsupported config) and redeploy
