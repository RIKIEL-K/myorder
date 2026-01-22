# Order & Notification Microservices

A application built with **FastAPI**, designed to be deployed on **Kubernetes** with **Redis** caching for high performance.

## Architecture

The application is split into two decoupled microservices:

1.  **Order Service**
    *   Handles order creation and dashboard display.
    *   ** Redis Caching**: Dashboard reads are cached for 30 seconds. New orders invalidate the cache instantly.
    *   **Frontend**: Jinja2 Templates (HTML/CSS).
    *   Communicates with *Notification Service* via internal K8s DNS.

2.  **Notification Service** 
    *   Handles email sending asynchronously using `fastapi-mail`.
    *   Logs all email events to a SQLite database.
    *   Exposes an Admin API for logs (`/admin/logs`).

3.  **Infrastructure Components**
    *   **Redis**: In-memory data store for caching order lists.
    *   **Nginx Ingress Controller**: Single entry point handling routing and rate limiting.
    *   **Kubernetes**: Orchestrates deployments, services, and secrets.

##  Technologies

*   **Python 3.10** & **FastAPI**
*   **Kubernetes (K8s)**: Deployments, Services, Ingress, Secrets.
*   **Redis**: Caching layer.
*   **Docker**: Containerization.
*   **SQLAlchemy**: ORM for SQLite.

##  Prerequisites

*   **Docker Desktop** or **Minikube** installed.
*   **Kubectl** CLI tool.
*   **Minikube Ingress Addon** enabled (`minikube addons enable ingress`).

## Kubernetes Deployment

### 1. Build Docker Images


### 2. Configure Secrets
Create `k8s/secrets.yaml` (copy from `k8s/secrets.yaml.example` if available or create manually):


### 3. Deploy Resources


##  Features Highlight

###  Redis Caching Strategy
*   **Hit**: `GET /` requests are served directly from Redis (Sub-millisecond latency).
*   **Miss**: Data fetched from DB, rendered, and stored in Redis.
*   **Invalidation**: `POST /create_order` automatically clears the cache key `orders_cache`.

###  Rate Limiting
*   **Ingress Annotation**: `nginx.ingress.kubernetes.io/limit-rps: "5"`
*   Protects the API from abuse by limiting clients to 5 requests per second.
