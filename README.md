# AUGS Infra-Agent (NL2I)

> **Natural Language to Infrastructure** — An AI-powered platform that converts plain English descriptions into production-ready AWS architectures, generates Terraform IaC, and deploys infrastructure with one click.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Code Structure](#code-structure)
- [AI Agent Pipeline](#ai-agent-pipeline)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Frontend Pages](#frontend-pages)
- [Security](#security)
- [Testing](#testing)

---

## Overview

Infra-Agent (NL2I) is a full-stack application that bridges the gap between natural language descriptions and cloud infrastructure. Users describe what they need (e.g., *"Build a serverless REST API with a DynamoDB backend"*) and the platform:

1. Interprets the intent using an AI agent
2. Designs an AWS architecture graph
3. Generates Terraform files
4. Estimates monthly costs
5. Produces an interactive visual diagram
6. Deploys the infrastructure to AWS with real-time log streaming

---

## Key Features

- **AI-Powered Design** — 6 specialized LLM agents orchestrate the full pipeline from natural language to deployed infrastructure
- **Interactive Architecture Editor** — Chat-based editing to refine generated architectures conversationally
- **Terraform Generation** — Auto-generates production `.tf` files from architecture graphs
- **One-Click Deployment** — Asynchronous Terraform execution via Celery with real-time WebSocket log streaming
- **Cost Analysis** — Per-service cost estimation, forecasting, and optimization recommendations
- **Visual Graph** — React Flow-powered interactive architecture diagrams with minimap and zoom controls
- **Monitoring Dashboard** — CloudWatch metrics integration for deployed resources
- **Secure Credential Storage** — AWS keys and LLM API keys encrypted at rest with Fernet (AES-128)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React 19)                      │
│         Vite · TypeScript · Tailwind CSS · React Flow           │
│                    http://localhost:5173                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST API + WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│                   http://localhost:8000                          │
│                                                                 │
│  ┌─────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐  │
│  │  Auth   │  │  AI Agents   │  │  Terraform  │  │ Monitoring│  │
│  │  (JWT)  │  │  (6 agents)  │  │  Executor   │  │ (CW/Cost) │  │
│  └─────────┘  └──────────────┘  └─────┬──────┘  └───────────┘  │
└───────┬───────────────┬───────────────┬─────────────────────────┘
        │               │               │
   ┌────▼────┐   ┌──────▼──────┐   ┌────▼────┐
   │ SQLite/ │   │   OpenAI /  │   │  Celery  │
   │ Postgres│   │ Compatible  │   │  Worker  │
   └─────────┘   │   LLM API   │   └────┬────┘
                 └─────────────┘        │
                                   ┌────▼────┐
                                   │  Redis   │
                                   │ (broker  │
                                   │ + pubsub)│
                                   └─────────┘
```

---

## Code Structure

```
Infra-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, CORS, router registration
│   │   ├── api/                     # API route handlers
│   │   │   ├── auth.py              #   Registration, login, JWT token issuance
│   │   │   ├── projects.py          #   Project CRUD operations
│   │   │   ├── architecture.py      #   AI generation, editing, cost estimation
│   │   │   ├── deployment.py        #   Terraform deploy/destroy, status tracking
│   │   │   ├── websocket.py         #   Real-time Terraform log streaming
│   │   │   ├── config.py            #   User preferences, AWS credential management
│   │   │   └── monitoring.py        #   CloudWatch metrics retrieval
│   │   ├── core/                    # Cross-cutting concerns
│   │   │   ├── config.py            #   Settings loaded from .env via Pydantic
│   │   │   ├── security.py          #   JWT, bcrypt, Fernet encryption utilities
│   │   │   └── deps.py              #   FastAPI dependency injection (DB session, auth)
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py              #   Users with encrypted AWS/LLM credentials
│   │   │   ├── project.py           #   User-owned projects
│   │   │   ├── architecture.py      #   Versioned architecture designs
│   │   │   ├── deployment.py        #   Terraform run history and logs
│   │   │   └── chat.py              #   Chat messages for architecture editing
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ai/                  # LLM agent orchestration
│   │   │   │   ├── base.py          #     OpenAI-compatible provider abstraction
│   │   │   │   ├── intent_agent.py  #     NL → structured intent extraction
│   │   │   │   ├── arch_agent.py    #     Intent → architecture graph
│   │   │   │   ├── edit_agent.py    #     Chat-based graph modifications
│   │   │   │   ├── terraform_agent.py #   Graph → Terraform file generation
│   │   │   │   ├── cost_agent.py    #     Graph → per-service cost breakdown
│   │   │   │   └── visual_agent.py  #     Graph → React Flow layout
│   │   │   ├── terraform/           # Infrastructure execution
│   │   │   │   ├── executor.py      #     Runs terraform init/plan/apply/destroy
│   │   │   │   ├── workspace_manager.py # Manages per-project workspaces
│   │   │   │   └── state_manager.py #     State file and drift detection
│   │   │   └── aws/                 # AWS integrations
│   │   │       └── cost_estimator.py#     Static pricing + LLM cost analysis
│   │   ├── prompts/                 # LLM instruction templates (Markdown)
│   │   ├── tasks/                   # Celery async tasks (Terraform jobs)
│   │   ├── db/                      # Database session factory and initialization
│   │   └── utils/                   # Graph validators, Terraform sanitizer, logging
│   ├── tests/                       # Pytest unit and integration tests
│   ├── alembic/                     # Database migration scripts
│   ├── Dockerfile                   # Python 3.11 + Terraform 1.7.5
│   ├── docker-compose.yml           # Full stack: backend, celery, postgres, redis
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Configuration template
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx                 # React 19 entry point
│   │   ├── App.tsx                  # React Router v7 route definitions
│   │   ├── index.css                # Tailwind directives + custom glass/glow theme
│   │   ├── pages/
│   │   │   ├── Login.tsx            #   Login form
│   │   │   ├── Register.tsx         #   Registration form
│   │   │   ├── Dashboard.tsx        #   Project listing and overview
│   │   │   ├── Settings.tsx         #   User preferences and AWS credentials
│   │   │   ├── Deployments.tsx      #   Deployment tracking across projects
│   │   │   ├── Monitoring.tsx       #   Infrastructure health dashboard
│   │   │   ├── CostAnalysis.tsx     #   Cost trends, forecasting, recommendations
│   │   │   └── projects/
│   │   │       ├── NewProject.tsx    #   Project creation form
│   │   │       ├── ProjectDetail.tsx #   Tabbed project view (3 tabs)
│   │   │       ├── ArchitectureTab.tsx # AI generation, chat editing, graph display
│   │   │       ├── DeploymentTab.tsx #   Deploy/destroy actions and log viewer
│   │   │       ├── MonitoringTab.tsx #   Per-project CloudWatch metrics
│   │   │       └── BlueprintGraph.tsx# React Flow interactive visualization
│   │   ├── components/
│   │   │   ├── Layout.tsx           #   Sidebar nav, responsive mobile menu
│   │   │   └── ProtectedRoute.tsx   #   Auth guard for protected pages
│   │   ├── context/
│   │   │   └── AuthContext.tsx       #   Global auth state (JWT, user session)
│   │   ├── api/                     # Axios-based API client modules
│   │   │   ├── client.ts            #   Base Axios instance with auth interceptor
│   │   │   ├── projects.ts          #   Project CRUD calls
│   │   │   ├── architecture.ts      #   Architecture generation and editing
│   │   │   ├── deployment.ts        #   Deploy/destroy/status calls
│   │   │   └── costAnalysis.ts      #   Cost summary, forecast, recommendations
│   │   └── types/
│   │       └── index.ts             #   TypeScript interfaces for all domains
│   ├── package.json                 # Dependencies and scripts
│   ├── vite.config.ts               # Vite bundler configuration
│   ├── tailwind.config.js           # Tailwind theme customization
│   └── tsconfig.json                # TypeScript compiler options
│
└── redis/                           # Windows Redis binaries (dev convenience)
```

---

## AI Agent Pipeline

When a user submits a natural language description, 6 specialized agents process it sequentially:

| # | Agent | Input | Output | Purpose |
|---|-------|-------|--------|---------|
| 1 | **Intent Agent** | Natural language text | `IntentOutput` (app type, scale, latency, storage needs) | Extracts structured requirements from free-form text |
| 2 | **Architecture Agent** | `IntentOutput` | `ArchitectureGraph` (nodes + edges) | Designs an AWS service graph meeting the requirements |
| 3 | **Terraform Agent** | `ArchitectureGraph` | `TerraformFileMap` (filename → HCL content) | Generates production `.tf` files for the architecture |
| 4 | **Cost Agent** | `ArchitectureGraph` | `CostEstimate` (per-service breakdown) | Estimates monthly AWS costs with free-tier considerations |
| 5 | **Visual Agent** | `ArchitectureGraph` | `VisualGraph` (React Flow JSON) | Produces layout data for interactive diagram rendering |
| 6 | **Edit Agent** | Graph + user chat message | Modified `ArchitectureGraph` | Conversationally refines the architecture on demand |

All agents use an **OpenAI-compatible LLM provider** — works with OpenAI, Azure OpenAI, Anthropic proxy, Ollama, or any compatible API.

---

## Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Async REST API framework |
| **SQLAlchemy (async)** | ORM with SQLite (dev) / PostgreSQL (prod) |
| **Alembic** | Database migrations |
| **Celery + Redis** | Async task queue for Terraform jobs |
| **WebSockets** | Real-time Terraform log streaming |
| **Terraform 1.7.5** | Infrastructure as Code execution |
| **OpenAI SDK** | LLM agent integration |
| **boto3** | AWS SDK (CloudWatch, cost APIs) |
| **Pydantic** | Request/response validation |
| **python-jose + bcrypt** | JWT authentication + password hashing |
| **Fernet (cryptography)** | Credential encryption at rest |

### Frontend
| Technology | Purpose |
|-----------|---------|
| **React 19** | UI framework |
| **TypeScript** | Type safety |
| **Vite 7** | Build tool with hot module replacement |
| **React Router v7** | Client-side routing |
| **Tailwind CSS 3.4** | Utility-first styling with dark theme |
| **React Flow (@xyflow/react)** | Interactive architecture graph visualization |
| **Axios** | HTTP client with auth interceptors |
| **Lucide React** | Icon library |
| **Framer Motion** | Animations |

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Redis** (for Celery task queue and WebSocket log streaming)
- **Terraform 1.7+** (for infrastructure deployment)
- An **OpenAI-compatible LLM API key** (OpenAI, Azure, Ollama, etc.)
- **AWS credentials** (for deployment and monitoring features)

### Local Development

**1. Backend**

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**2. Celery Worker** (separate terminal)

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

**3. Frontend**

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend runs at `http://localhost:5173` and the API at `http://localhost:8000`.

### Docker Deployment

Run the full stack (backend, Celery worker, PostgreSQL, Redis) with Docker Compose:

```bash
cd backend

# Configure environment
cp .env.example .env
# Edit .env with your LLM_API_KEY and other settings

# Start all services
docker-compose up --build
```

This starts:
- **Backend API** on port `8000`
- **Celery Worker** for async Terraform operations
- **PostgreSQL 16** on port `5432`
- **Redis 7** on port `6379`

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./nl2i.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret | *(required)* |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | `60` |
| `LLM_BASE_URL` | LLM API base URL | `https://api.openai.com/v1` |
| `LLM_API_KEY` | LLM API key | *(required)* |
| `LLM_MODEL` | LLM model name | `gpt-4o` |
| `AWS_DEFAULT_REGION` | Default AWS region | `us-east-1` |
| `TERRAFORM_WORKSPACES_DIR` | Terraform workspace path | `./workspaces` |
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet key for credential encryption | *(required)* |

See [`backend/.env.example`](backend/.env.example) for the full configuration template.


## MVP
<img width="1919" height="969" alt="Screenshot 2026-02-26 134019" src="https://github.com/user-attachments/assets/ea1acddd-fd7c-43d4-a49a-93ea9a76cd74" />
<img width="1918" height="969" alt="Screenshot 2026-02-26 134028" src="https://github.com/user-attachments/assets/72f534e3-1867-4b11-bafd-0965b8bafe76" />
<img width="1919" height="967" alt="Screenshot 2026-02-26 134034" src="https://github.com/user-attachments/assets/bd542dca-9941-4444-a2b8-b46516e630f5" />
<img width="1919" height="971" alt="Screenshot 2026-02-26 134041" src="https://github.com/user-attachments/assets/aeecf5a4-9bd0-4f04-840f-cecf2f1c6a81" />
<img width="1919" height="970" alt="Screenshot 2026-02-26 134056" src="https://github.com/user-attachments/assets/6a32fa12-35bd-4fdf-94e9-f301309d131f" />
<img width="1919" height="969" alt="Screenshot 2026-02-26 134113" src="https://github.com/user-attachments/assets/23f30f3f-b233-4eec-8a7e-bf90cc261f67" />
<img width="1919" height="970" alt="Screenshot 2026-02-26 134123" src="https://github.com/user-attachments/assets/ced36dee-bf33-40fe-af94-542567339b26" />
<img width="1919" height="972" alt="Screenshot 2026-02-26 134131" src="https://github.com/user-attachments/assets/67a74b3d-880f-4f0b-8910-a83e600ac93e" />


---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/login` | Authenticate and receive JWT token |
| `GET` | `/auth/me` | Get current user profile |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/` | Create a new project |
| `GET` | `/projects/` | List all user projects |
| `GET` | `/projects/{id}` | Get project details |
| `DELETE` | `/projects/{id}` | Delete project and workspace |

### Architecture
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/generate` | Run AI pipeline (intent → architecture → terraform → cost → visual) |
| `POST` | `/projects/{id}/edit` | Edit architecture via chat message |
| `GET` | `/projects/{id}/architecture` | Get latest architecture and Terraform files |
| `GET` | `/projects/{id}/cost` | Get cost estimate |

### Deployment
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/deploy` | Trigger `terraform apply` (async) |
| `POST` | `/projects/{id}/destroy` | Trigger `terraform destroy` (async) |
| `GET` | `/projects/{id}/status` | Get current deployment status |
| `GET` | `/projects/{id}/deployments` | Get deployment history |

### Real-Time Logs
| Method | Endpoint | Description |
|--------|----------|-------------|
| `WS` | `/projects/{id}/logs` | WebSocket stream of Terraform execution logs |

### Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/config/` | Get user preferences |
| `PUT` | `/config/` | Update user preferences |
| `PUT` | `/config/aws-credentials` | Store encrypted AWS credentials |

### Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/{id}/metrics` | Get CloudWatch metrics for deployed resources |

---

## Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/login` | Login | Email and password authentication |
| `/register` | Register | New account creation |
| `/` | Dashboard | Project listing with status badges and quick actions |
| `/projects/new` | New Project | Project creation with natural language input |
| `/projects/:id` | Project Detail | Tabbed view — **Architecture**, **Deployment**, **Monitoring** |
| `/deployments` | Deployments | Cross-project deployment tracking and status |
| `/monitoring` | Monitoring | System-wide infrastructure health |
| `/cost-analysis` | Cost Analysis | Cost trends, forecasting charts, and AI recommendations |
| `/settings` | Settings | User preferences and AWS credential management |

---

## Security

- **JWT Authentication** — All protected endpoints require a Bearer token
- **Password Hashing** — bcrypt with salt rounds
- **Credential Encryption** — AWS keys and LLM API keys encrypted at rest using Fernet (AES-128 in CBC mode)
- **Terraform Sanitization** — Blocks dangerous provisioners (`local-exec`, `remote-exec`, `null_resource`, `external` data sources)
- **AWS Service Whitelist** — Only 14 approved services permitted (Lambda, API Gateway, DynamoDB, RDS, ECS, S3, CloudFront, SQS, SNS, ElastiCache, VPC, ELB, Route53, ECR)
- **Graph Validation** — Detects duplicate nodes, self-loops, and invalid edges before processing
- **Auth Interceptors** — Frontend auto-clears tokens on 401 responses

---

## Testing

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_api.py -v          # API endpoint tests
pytest tests/test_schemas.py -v      # Schema validation tests
pytest tests/test_validators.py -v   # Graph and Terraform validation
pytest tests/test_cost_estimator.py -v # Cost estimation logic
```

Tests use an in-memory SQLite database and include async fixtures for the FastAPI test client.
