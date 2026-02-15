# NL2I — AI-Powered AWS Infrastructure Designer & Deployer

> Convert natural language → AWS architecture → Terraform IaC → Deployed infrastructure.

NL2I is a production-ready backend system that uses AI agents to design, deploy, and manage AWS infrastructure from plain English descriptions. Built with FastAPI, it provides a complete pipeline from natural language requirements to live cloud infrastructure.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **NL → Architecture** | Convert plain English to AWS architecture graphs using AI |
| 💬 **Chat-Based Editing** | Modify architectures through conversation |
| 📐 **Terraform Generation** | Auto-generate production-ready Terraform IaC |
| 🚀 **One-Click Deploy** | Deploy infrastructure via Terraform with async job tracking |
| 💰 **Cost Estimation** | Get monthly cost estimates before deploying |
| 📊 **Visual Architecture** | React Flow-compatible graph JSON for frontend visualization |
| 📈 **Infra Monitoring** | CloudWatch metrics for deployed resources |
| 🔐 **Secure Credentials** | Encrypted AWS credential storage with JWT auth |
| 🐳 **Dockerized** | Single-command deployment with Docker Compose |

---

## 🏗 Architecture

```
React (Vite) Frontend
        ↓
   FastAPI Backend
        ↓
  AI Orchestrator Layer
  ├── Intent Agent         (NL → structured intent)
  ├── Architecture Agent   (intent → AWS graph)
  ├── Edit Agent           (graph + prompt → modified graph)
  ├── Terraform Agent      (graph → .tf files)
  ├── Cost Agent           (graph → cost estimate)
  └── Visual Agent         (graph → React Flow JSON)
        ↓
  Terraform Executor (sandboxed per-project workspace)
        ↓
      AWS
```

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.11+**
- **Terraform CLI** (auto-installed via Docker, or install manually)
- **Redis** (optional for dev — required for async deployments)
- **PostgreSQL** (optional — SQLite used by default for dev)

### 1. Clone & Setup

```bash
cd backend
cp .env.example .env
# Edit .env with your LLM API key and preferences
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the API Docs

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

---

## 🐳 Docker Deployment

```bash
cd backend
cp .env.example .env
# Edit .env with your settings

docker-compose up --build
```

This starts:
- **Backend API** on port `8000`
- **Celery Worker** for async terraform jobs
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`

---

## ⚙️ Configuration

All configuration is via environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./nl2i.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret | `change-me-...` |
| `LLM_BASE_URL` | LLM API endpoint (OpenAI-compatible) | `https://api.openai.com/v1` |
| `LLM_API_KEY` | LLM API key | — |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `AWS_DEFAULT_REGION` | Default AWS region | `us-east-1` |
| `TERRAFORM_WORKSPACES_DIR` | Terraform workspace directory | `./workspaces` |
| `CREDENTIAL_ENCRYPTION_KEY` | Key for encrypting stored AWS credentials | `change-me-...` |

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login and get JWT token |
| `GET` | `/auth/me` | Get current user |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/` | Create a new project |
| `GET` | `/projects/` | List all projects |
| `GET` | `/projects/{id}` | Get project details |
| `DELETE` | `/projects/{id}` | Delete a project |

### Architecture
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/generate` | Generate architecture from NL |
| `POST` | `/projects/{id}/edit` | Edit existing architecture |
| `GET` | `/projects/{id}/architecture` | Get latest architecture |
| `GET` | `/projects/{id}/cost` | Get cost estimate |

### Deployment
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/deploy` | Trigger terraform apply |
| `POST` | `/projects/{id}/destroy` | Trigger terraform destroy |
| `GET` | `/projects/{id}/status` | Get deployment status |
| `GET` | `/projects/{id}/deployments` | List all deployments |

### Monitoring & Config
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/{id}/metrics` | Get CloudWatch metrics |
| `GET` | `/config/` | Get user preferences |
| `PUT` | `/config/` | Update preferences |
| `PUT` | `/config/aws-credentials` | Store AWS credentials |

### WebSocket
| Protocol | Endpoint | Description |
|----------|----------|-------------|
| `WS` | `/projects/{id}/logs` | Stream terraform execution logs |

---

## 🧠 AI Agents

Each agent is a stateless module with a single `run()` method:

| Agent | Input | Output |
|-------|-------|--------|
| **Intent Agent** | Natural language text | Structured intent (app type, scale, etc.) |
| **Architecture Agent** | Intent JSON | Architecture graph (nodes + edges) |
| **Edit Agent** | Graph + modification prompt | Modified graph |
| **Terraform Agent** | Architecture graph | Terraform file map |
| **Cost Agent** | Architecture graph | Cost estimate with breakdown |
| **Visual Agent** | Architecture graph | React Flow-compatible layout |

All LLM prompts are stored as markdown files in `app/prompts/` for easy editing.

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

Test coverage:
- **Schema validation** — Pydantic model serialization
- **Validators** — Graph validation, Terraform sanitization
- **Cost estimation** — Static pricing calculations
- **API integration** — Auth, projects, config, deployments

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── api/                    # API route handlers
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── architecture.py
│   │   ├── deployment.py
│   │   ├── websocket.py
│   │   ├── config.py
│   │   └── monitoring.py
│   ├── core/                   # Config, security, dependencies
│   │   ├── config.py
│   │   ├── security.py
│   │   └── deps.py
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── architecture.py
│   │   ├── deployment.py
│   │   └── chat.py
│   ├── schemas/                # Pydantic validation schemas
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── architecture.py
│   │   ├── deployment.py
│   │   └── chat.py
│   ├── services/
│   │   ├── ai/                 # AI Agent modules
│   │   │   ├── base.py         # LLM provider abstraction
│   │   │   ├── intent_agent.py
│   │   │   ├── architecture_agent.py
│   │   │   ├── edit_agent.py
│   │   │   ├── terraform_agent.py
│   │   │   ├── cost_agent.py
│   │   │   └── visual_agent.py
│   │   ├── terraform/          # Terraform execution layer
│   │   │   ├── executor.py
│   │   │   ├── workspace_manager.py
│   │   │   └── state_manager.py
│   │   └── aws/                # AWS service integrations
│   │       ├── cost_estimator.py
│   │       └── cloudwatch.py
│   ├── prompts/                # LLM prompt templates (.md files)
│   │   ├── intent_agent_prompt.md
│   │   ├── architecture_agent_prompt.md
│   │   ├── edit_agent_prompt.md
│   │   ├── terraform_agent_prompt.md
│   │   ├── cost_agent_prompt.md
│   │   └── visual_agent_prompt.md
│   ├── tasks/                  # Celery async tasks
│   │   ├── celery_app.py
│   │   └── deployment_tasks.py
│   ├── db/                     # Database setup
│   │   ├── base.py
│   │   └── session.py
│   └── utils/                  # Utilities
│       ├── validators.py
│       ├── logging.py
│       └── prompt_loader.py
├── tests/                      # Test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## 🔐 Security

- **JWT Authentication** — All endpoints secured with bearer tokens
- **Encrypted Credentials** — AWS keys stored with Fernet encryption
- **Terraform Sanitization** — Blocks `local-exec`, `remote-exec`, and other dangerous patterns
- **Service Whitelist** — Only approved AWS service types allowed in architectures
- **Graph Validation** — Architecture graphs validated before Terraform generation
- **No Secret Logging** — AWS credentials never appear in logs

---

## 🚀 Future Extensions (Hooks Prepared)

- **Multi-Cloud** — Provider abstraction layer ready for GCP/Azure
- **Drift Detection** — State manager has `detect_drift()` hook
- **Cost Anomaly Detection** — Cost agent supports LLM-based analysis
- **Visual Drag-and-Drop** — Visual agent outputs React Flow-compatible JSON
- **RBAC Roles** — User model extensible for role-based access
- **Alembic Migrations** — Config ready for production schema migrations

---

## 📝 License

MIT
