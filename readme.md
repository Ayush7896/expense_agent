---

# 🎯 **How Everything Connects (The Full Flow)**

## **Example: User asks "Add $50 lunch expense"**
```
1. FastAPI receives POST /chat
   ├─> api.py: chat_endpoint()
   │
2. Call agent
   ├─> agent.py: chat_with_agent()
   │   │
3. Agent reasoning
   │   ├─> LangGraph: agent_reasoning_node()
   │   ├─> LLM generates JSON:
   │   │   {
   │   │     "thought": "Need to add expense",
   │   │     "needs_tool": true,
   │   │     "tool_name": "add_expense",
   │   │     "tool_input": {"amount": 50, "category": "food", "description": "lunch"}
   │   │   }
   │   │
4. Parse with Pydantic (NO REGEX!)
   │   ├─> AgentThought(**json_data)
   │   │
5. Route decision
   │   ├─> should_continue() → "execute_tool"
   │   │
6. Execute tool
   │   ├─> tool_execution_node()
   │   ├─> tools.py: add_expense_tool()
   │   │   │
7. Database operation
   │   │   ├─> database.py: ExpenseRepository.create_expense()
   │   │   ├─> PostgreSQL: INSERT INTO expenses...
   │   │   │
8. Return result
   │   │   ├─> ToolResult(success=True, message="...")
   │   │   │
9. Agent sees result
   │   │   ├─> Added to conversation_history
   │   │   ├─> Back to agent_reasoning_node()
   │   │   │
10. Agent responds
    │   ├─> LLM generates:
    │   │   {
    │   │     "thought": "Task complete",
    │   │     "needs_tool": false,
    │   │     "final_answer": "I've added your $50 lunch expense to the food category!"
    │   │   }
    │   │
11. Return to user
    ├─> FastAPI: ChatResponse
    └─> User gets: {"answer": "I've added...", "steps_taken": 2, ...}

```
---

# 🚀 Deployment: From Basic to Advanced

This project is a FastAPI service with a PostgreSQL database. Deployment answers four core questions:

1. **How does someone call my code?** → An API (FastAPI endpoints in `api.py`)
2. **Where does my code run?** → A server or container (Uvicorn + Docker)
3. **How does it get config/secrets?** → Environment variables, `.env`, or secrets manager
4. **How do I run it reliably?** → Docker + CI/CD pipeline

Below are the exact files that implement those answers, plus a clear explanation of *why* each one exists.

---

## ✅ 1) API: "How does someone call my code?"

FastAPI exposes HTTP endpoints so your app is callable from any client:

- `POST /chat` for the agent chat flow
- `GET /health` for health checks

This is already defined in `api.py` and served by Uvicorn in `main.py`.

---

## ✅ 2) Runtime: "Where does my code run?"

We containerize the app so it can run anywhere (local machine, AWS, Azure, GCP).

### **Dockerfile**
This builds your app into an image:

```
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy psycopg2-binary
EXPOSE 8000
CMD ["python", "main.py"]
```

**Why?**
- Consistent runtime everywhere
- Easy to deploy on cloud or local

---

## ✅ 3) Config & Secrets: "How does it get configuration?"

The database URL is now loaded from environment variable `DATABASE_URL`.
That means:

- Local: `.env`
- Cloud: secrets manager or environment variables

### `.env.example`
```
DATABASE_URL=postgresql://postgres:postgres@db:5432/agent_campusx
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=agent_campusx
```

Copy to `.env` locally:
```
cp .env.example .env
```

---

## ✅ 4) Reliability: "How do I run it again and again?"

We use Docker + Compose to run the same setup repeatedly.

### **docker-compose.yml**
This runs API + PostgreSQL together:

```
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
```

Run it:
```
docker compose --env-file .env up --build
```

---

# ✅ CI/CD: Run tests automatically on every push

We added a GitHub Actions workflow so every push checks imports (basic sanity test).

### `.github/workflows/ci.yml`
```yaml
name: CI
on:
  push:
    branches: ["main"]
  pull_request:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install fastapi uvicorn sqlalchemy psycopg2-binary
      - run: python - <<'PY'
          import api, database, agent, models
          print("✅ Imports OK")
          PY
```

---

# 🌍 Cloud Deployment (AWS / Azure / GCP)

Once it runs in Docker, any cloud just runs your container.

## ✅ AWS (ECS + RDS)
1. Push image to **ECR**
2. Create Postgres on **RDS**
3. Run container on **ECS Fargate**
4. Set `DATABASE_URL` as environment variable
5. Add Load Balancer + HTTPS

## ✅ Azure (Container Apps + Azure DB for Postgres)
1. Push image to ACR
2. Create Postgres on Azure
3. Deploy Container App
4. Set `DATABASE_URL` in app config

## ✅ GCP (Cloud Run + Cloud SQL)
1. Build + push image to GCR or Artifact Registry
2. Create Cloud SQL Postgres
3. Deploy to Cloud Run
4. Connect secrets via Secret Manager

---

# ✅ Summary

| Question | Answer | File |
|----------|--------|------|
| How do I call my code? | FastAPI endpoints | `api.py` |
| Where does it run? | Docker container | `Dockerfile` |
| How config is loaded? | Environment variables | `.env.example` |
| How to run repeatedly? | Docker + Compose | `docker-compose.yml` |
| How to automate checks? | GitHub Actions | `.github/workflows/ci.yml` |

---