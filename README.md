# Project Gutenberg — Backend

Django REST API for the **Project Gutenberg Book Analysis** application. The backend fetches public-domain books from [Project Gutenberg](https://www.gutenberg.org/), analyzes their content with LLMs, stores vector embeddings for semantic search, and exposes authenticated endpoints for book discovery, analysis, and conversational Q&A.

## Features

- Fetch book **content** and **metadata** from Project Gutenberg
- **LLM-powered analysis** (summary, characters, themes, sentiment, quotes) via Groq
- **Semantic search** over book chunks using Gemini embeddings and pgvector
- **Conversational Q&A** about a book with retrieval-augmented context
- **JWT authentication** (signup / login)
- **Search history** per authenticated user
- Background processing with **Celery** and **Redis**
- Optional **OpenTelemetry** tracing and logging

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 5, Django Ninja |
| Database | PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector) |
| Task queue | Celery, Redis |
| LLMs | Groq (analysis), Google Gemini (embeddings) |
| Server | Gunicorn (production / Docker / K8s) |
| Observability | OpenTelemetry (optional) |

## Prerequisites

- **Python** 3.12+
- **PostgreSQL** 16+ with the `pgvector` extension (or use Docker / K8s manifests)
- **Redis** 6+
- API keys: [Groq](https://console.groq.com/) and [Google Gemini](https://aistudio.google.com/)

For Kubernetes deployment you also need [Kind](https://kind.sigs.k8s.io/), [kubectl](https://kubernetes.io/docs/tasks/tools/), [kubeseal](https://github.com/bitnami-labs/sealed-secrets), and Docker.

---

## Environment Variables

Copy the example file and fill in your values:

```bash
cp config/.env.example config/.env
```

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local development |
| `LIVE_ENV` | Set to `False` for local / dev |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL credentials (used by Docker Compose `db` service) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `GROQ_API_KEY`, `GROQ_LLM_MODEL` | Groq API credentials and model |
| `GEMINI_API_KEY`, `GEMINI_EMBEDDING_MODEL` | Gemini API credentials and embedding model |
| `CHUNKING_MODEL` | Model name used for text chunking tokenization |
| `OTEL_ENABLE_TRACING` | `True` to enable OpenTelemetry (optional) |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_TOKEN` | OTLP exporter settings (optional) |

**Local example** (`config/.env`):

```env
SECRET_KEY=your-secret-key
DEBUG=True
LIVE_ENV=False

POSTGRES_DB=gutenberg
POSTGRES_USER=gutenberg
POSTGRES_PASSWORD=gutenberg
DATABASE_URL=postgres://gutenberg:gutenberg@localhost:5432/gutenberg

GROQ_API_KEY=your_groq_api_key
GROQ_LLM_MODEL=llama-3.1-8b-instant

GEMINI_API_KEY=your_gemini_api_key
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
CHUNKING_MODEL=gpt-4o-mini

REDIS_URL=redis://localhost:6379/0

OTEL_ENABLE_TRACING=False
```

**Docker Compose** — use service hostnames instead of `localhost`:

```env
DATABASE_URL=postgres://gutenberg:gutenberg@db:5432/gutenberg
REDIS_URL=redis://redis:6379/0
```

---

## Local Development

### 1. Clone and set up Python

```bash
git clone https://github.com/OthLah001/project-gutenberg-be.git
cd project-gutenberg-be

python -m venv env
source env/bin/activate          # macOS / Linux
# env\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 2. Start PostgreSQL and Redis

Run PostgreSQL (with pgvector) and Redis locally, or start only the data services from Docker Compose:

```bash
docker compose up db redis -d
```

If using Docker for the databases, make sure `DATABASE_URL` and `REDIS_URL` in `config/.env` point to `localhost` (ports `5432` and `6379` are published).

### 3. Apply migrations

```bash
python manage.py migrate
```

### 4. (Optional) Seed book catalog

Import metadata from the Project Gutenberg catalog CSV:

```bash
python manage.py fetch_books_data_from_csv
```

### 5. Start Celery worker

In a separate terminal (with the virtual environment activated):

```bash
celery -A config worker --loglevel=info
```

### 6. Run the development server

```bash
python manage.py runserver
```

The API is available at **http://127.0.0.1:8000/**

---

## Docker

Docker Compose runs the full stack: PostgreSQL (pgvector), Redis, the Django web server (Gunicorn), and a Celery worker.

### 1. Configure environment

```bash
cp config/.env.example config/.env
```

Update `DATABASE_URL` and `REDIS_URL` to use Docker service names (`db` and `redis`) as shown in the [Environment Variables](#environment-variables) section.

### 2. Build and start

```bash
docker compose up --build
```

Services:

| Service | Container | Port |
|---------|-----------|------|
| Web (Django + Gunicorn) | `g_django` | 8000 |
| Celery worker | `g_celery_worker` | — |
| PostgreSQL (pgvector) | `g_db` | 5432 |
| Redis | `g_redis` | 6379 |

Migrations run automatically when the `web` container starts. The API is available at **http://localhost:8000/**

### Useful commands

```bash
# Run in the background
docker compose up -d

# View logs
docker compose logs -f web celery_worker

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## Kubernetes (Kind)

Manifests under `deployment/` provision a local [Kind](https://kind.sigs.k8s.io/) cluster with PostgreSQL, Redis, and the backend API. Secrets are encrypted with [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets).

### 1. Prepare secrets

Create `deployment/env-config/secrets.yml` from the example and replace placeholder values with your real credentials:

```bash
cp deployment/env-config/secrets.example.yaml deployment/env-config/secrets.yml
# Edit secrets.yml with your SECRET_KEY, database credentials, and API keys
```

The `DATABASE_URL` in secrets should use the in-cluster Postgres service:

```
postgres://<user>:<password>@gutenberg-postgres-service:5432/<db>
```

### 2. Deploy with the helper script

```bash
chmod +x k8s-script.sh
./k8s-script.sh
```

The script will:

1. Optionally create a Kind cluster (`gutenberg-kind-cluster`) from `deployment/kind-config.yaml`
2. Install the Sealed Secrets controller and encrypt `secrets.yml` into `sealedsecret.yaml`
3. Build the Docker image and load it into the Kind cluster
4. Apply ConfigMaps, Secrets, Postgres, Redis, migration Job, backend Deployment, and Celery worker

On subsequent runs, choose **n** when asked to create a new cluster to rebuild the image and roll out an updated backend and Celery worker.

### 3. Access the API

The backend is exposed via NodePort **30800**:

**http://localhost:30800/**

### Manual deployment (without the script)

```bash
kind create cluster --config deployment/kind-config.yaml

docker build -t localhost:5000/gutenberg-backend:local .
kind load docker-image localhost:5000/gutenberg-backend:local --name gutenberg-kind-cluster

kubectl apply -f deployment/env-config/configmap.yaml
kubectl apply -f deployment/env-config/sealedsecret.yaml
kubectl apply -f deployment/db-config/
kubectl wait --for=condition=ready pod/gutenberg-postgres-0 --timeout=120s
kubectl wait --for=condition=available deployment/gutenberg-redis --timeout=120s

kubectl apply -f deployment/backend-config/migrate-job.yaml
kubectl wait --for=condition=complete job/gutenberg-migrate --timeout=120s

kubectl apply -f deployment/backend-config/backend.yaml
kubectl apply -f deployment/backend-config/celery.yaml
```

### Deployment layout

```
deployment/
├── kind-config.yaml          # Kind cluster config (NodePort 30800)
├── env-config/
│   ├── configmap.yaml        # Non-sensitive env vars
│   ├── secrets.example.yaml  # Secret template
│   └── sealedsecret.yaml     # Encrypted secrets (generated)
├── db-config/
│   ├── postgres.yaml         # Postgres StatefulSet + Service
│   ├── postgres-storage.yaml # StorageClass
│   ├── redis.yaml            # Redis Deployment + Service
│   └── redis-storage.yaml    # StorageClass
└── backend-config/
    ├── backend.yaml          # Backend Deployment + NodePort Service
    ├── celery.yaml           # Celery worker Deployment
    └── migrate-job.yaml      # One-off Django migrate Job
```

---

## API Documentation

Django Ninja auto-generates interactive OpenAPI docs per API namespace:

| API | Docs URL |
|-----|----------|
| Books (authenticated) | http://127.0.0.1:8000/api/books/docs |
| Auth | http://127.0.0.1:8000/api/auth/docs |

### Main endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/auth/signup/` | No | Register a new user |
| `POST` | `/api/auth/login/` | No | Log in and receive a JWT |
| `GET` | `/api/books/{id}/content/` | Yes | Fetch book text |
| `GET` | `/api/books/{id}/metadata/` | Yes | Fetch metadata and trigger analysis |
| `GET` | `/api/books/{id}/analysis/` | Yes | Get LLM analysis results |
| `GET` | `/api/books/history/` | Yes | User search history |
| `GET` | `/api/books/search/?query=` | Yes | Semantic book search |
| `POST` | `/api/books/ask/` | Yes | Ask a question about a book |

---

## License

See [LICENSE](LICENSE).
