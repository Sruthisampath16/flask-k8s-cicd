# Flask K8s CI/CD — Zero-Downtime Deployment Pipeline with Postgres

A Flask application deployed to Kubernetes with a complete CI/CD pipeline built on **Git, GitHub Actions, Docker, and Kubernetes**, backed by an in-cluster **Postgres** database with real connectivity health checks.

## What this project demonstrates

- Multi-stage Docker builds with a non-root runtime user
- Kubernetes Deployments with a zero-downtime rolling update strategy
- Readiness and liveness probes as the actual mechanism behind zero-downtime
- A stateful in-cluster database (Postgres) with persistent storage and Secrets-based credentials
- Kubernetes service discovery — the app finds the database purely by Service name, no hardcoded IPs
- A CI pipeline (test → build → push) automated via GitHub Actions
- Manual deploy to a local Kubernetes cluster, with a documented path to full deploy automation on AWS EKS

## Architecture

```
Push to main
     │
     ▼
GitHub Actions: run tests (pytest)
     │
     ▼
GitHub Actions: build Docker image, push to Docker Hub
     │
     ▼
Manual: kubectl set image (rolling update)
     │
     ▼
Kubernetes rolls out new Flask pods one at a time
     │
     ▼
Each pod's /readyz checks a live connection to Postgres
(via the postgres-service Kubernetes Service — resolved
by internal cluster DNS, no hardcoded IP)
```

## Tech stack

| Layer | Tool |
|---|---|
| App | Flask (Python 3.12) |
| WSGI server | Gunicorn |
| Database | PostgreSQL 16, running in-cluster |
| DB driver | psycopg2-binary |
| Containerization | Docker (multi-stage build) |
| Orchestration | Kubernetes (Docker Desktop, local) |
| CI | GitHub Actions |
| Image registry | Docker Hub |

## Project structure

```
flask-k8s-cicd/
├── app/
│   ├── app.py              # Flask app: /, /healthz, /readyz (real DB check)
│   ├── requirements.txt
│   └── test_app.py
├── k8s/
│   ├── deployment.yaml       # Flask Deployment: rolling update, probes, DB env vars
│   ├── service.yaml          # Flask Service (NodePort)
│   ├── postgres-deployment.yaml   # Postgres Deployment, backed by a PVC
│   ├── postgres-service.yaml      # Postgres Service (ClusterIP, internal only)
│   ├── postgres-pvc.yaml          # PersistentVolumeClaim for Postgres data
│   └── postgres-secret.yaml       # DB credentials (Opaque Secret)
├── .github/workflows/
│   └── cicd.yaml
├── Dockerfile
└── README.md
```

## How the database is wired up

- **Postgres runs as its own single-replica Deployment**, backed by a `PersistentVolumeClaim` so data survives pod deletion (not just restarts).
- **Credentials live in a Kubernetes Secret**, referenced by both the Postgres pod and the Flask pods via `envFrom: secretRef` — the password is never hardcoded in any YAML the app reads at runtime.
- **Flask finds Postgres by Service name alone** (`postgres-service`) — Kubernetes' internal DNS resolves this automatically to whichever pod is currently healthy, with zero manual IP configuration.
- **`/readyz` performs a real connection check**, not a static response — if Postgres is unreachable, it returns a `503` with the actual error, and Kubernetes' readiness probe correctly stops routing traffic to that pod.

## How zero-downtime is achieved

- **Rolling update strategy** (`maxUnavailable: 0`, `maxSurge: 1`)
- **Readiness probe** (`/readyz`) — now checks real DB connectivity, so a pod that can't reach the database is correctly excluded from traffic
- **Liveness probe** (`/healthz`) — restarts pods that stop responding

## CI/CD pipeline

Two automated jobs run on every push to `main`:
1. **test** — pytest against all three routes
2. **build-and-push** — builds and pushes the Docker image to Docker Hub

**Known limitation, by design:** `test_readyz` currently expects either a `200` or `503` response rather than asserting a live database exists, since GitHub Actions' runners have no Kubernetes cluster or Postgres instance available. A `503` in CI is the *correct*, expected outcome — the endpoint is doing its job.

## Deployment status (current)

Deploy is manual, run locally against Docker Desktop's Kubernetes — GitHub Actions' cloud runners have no network path to a cluster running on a laptop. See "Planned: AWS EKS migration" below.

```bash
kubectl set image deployment/flask-app flask-app=sruthidoc07/flask-k8s-cicd:latest
kubectl rollout status deployment/flask-app
```

## Planned: AWS EKS migration

Moving the cluster to AWS EKS would make deploy fully automatable via a `KUBE_CONFIG` GitHub Secret and a re-added `deploy` job — no other pipeline logic changes required.

## Local testing

```bash
# Deploy everything
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

kubectl get pods
kubectl get endpoints postgres-service   # confirm Postgres has a real endpoint

# Access the app
kubectl port-forward svc/flask-app-cicd 8080:80
curl http://localhost:8080/readyz
# {"status": "ready", "database": "connected"}
```

## What I'd improve with more time

- Complete the AWS EKS migration for fully automated deploy
- Mock the database in `test_readyz`'s test instead of accepting either status code, for a more precise test
- Add a staging namespace and promote images staging → prod
- Add Prometheus/Grafana for real rollout metrics
- Move from NodePort to an Ingress controller with a real domain

## Security hardening applied

This deployment's `k8s/deployment.yaml` now includes pod- and container-level `securityContext` settings (`runAsNonRoot`, an explicit numeric `runAsUser`, dropped Linux capabilities, `allowPrivilegeEscalation: false`, and a seccomp profile), enforced via the `restricted` Pod Security Standard on the namespace. This was developed and documented as part of a separate, dedicated project — [security-hardened-kubernetes-platform](https://github.com/Sruthisampath16/Security-Hardened-Kubernetes-Platform) — which also covers RBAC, NetworkPolicy, and container image vulnerability scanning against this same Flask image.