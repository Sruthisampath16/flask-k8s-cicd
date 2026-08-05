# Flask K8s CI/CD — Zero-Downtime Deployment Pipeline

A Flask application deployed to Kubernetes with a complete CI/CD pipeline built on **Git, GitHub Actions, Docker, and Kubernetes** — no cloud-native CI/CD services used, to keep the toolchain portable across any cloud provider.

## What this project demonstrates

- Multi-stage Docker builds with a non-root runtime user
- Kubernetes Deployments with a zero-downtime rolling update strategy
- Readiness and liveness probes as the actual mechanism behind zero-downtime, not just a strategy setting
- A CI pipeline (test → build → push) fully automated via GitHub Actions
- Manual deploy to a local Kubernetes cluster, with a clear, documented path to full deploy automation on AWS EKS

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
Manual: kubectl set image (rolling update) — see "Deployment status" below
     │
     ▼
Kubernetes rolls out new pods one at a time,
old pods stay serving traffic until new ones pass
the readiness probe → zero dropped requests
```

## Tech stack

| Layer | Tool |
|---|---|
| App | Flask (Python 3.12) |
| WSGI server | Gunicorn |
| Containerization | Docker (multi-stage build) |
| Orchestration | Kubernetes (Docker Desktop, local) |
| CI | GitHub Actions |
| Image registry | Docker Hub |

## Project structure

```
flask-k8s-cicd/
├── app/
│   ├── app.py              # Flask app with /, /healthz, /readyz routes
│   ├── requirements.txt
│   └── test_app.py         # pytest tests, run automatically in CI
├── k8s/
│   ├── deployment.yaml      # Rolling update strategy, probes, resource limits
│   └── service.yaml         # NodePort service exposing the app
├── .github/workflows/
│   └── cicd.yaml            # test + build-and-push jobs
├── Dockerfile
└── README.md
```

## How zero-downtime is achieved

- **Rolling update strategy** (`maxUnavailable: 0`, `maxSurge: 1`) — the deployment never has fewer than the desired number of healthy pods running during an update.
- **Readiness probe** (`/readyz`) — Kubernetes does not route traffic to a new pod until it reports ready. This is the actual mechanism that prevents dropped requests, not the rolling strategy alone.
- **Liveness probe** (`/healthz`) — Kubernetes restarts pods that stop responding.

## CI/CD pipeline

The GitHub Actions workflow (`.github/workflows/cicd.yaml`) runs two automated jobs on every push to `main`:

1. **test** — installs dependencies, runs `pytest` against all three routes
2. **build-and-push** — builds the Docker image and pushes it to Docker Hub, tagged with both the commit SHA and `latest`

## Deployment status (current)

**The deploy step is currently manual, run locally against Docker Desktop's Kubernetes cluster.** This is a deliberate, documented decision, not an oversight:

- GitHub Actions runners are cloud-hosted and have no network path to a Kubernetes cluster running on a local machine
- Automating this step would require the cluster to be internet-reachable (e.g. AWS EKS), which has an ongoing cost even at the smallest scale
- The pipeline's CI portion (test, build, push) is fully automated and green; only the final `kubectl` deploy command is run by hand, using the exact same command an automated step would use

To deploy manually after a new image is pushed:
```bash
kubectl set image deployment/flask-app flask-app=sruthidoc07/flask-k8s-cicd:latest
kubectl rollout status deployment/flask-app
```

## Planned: AWS EKS migration

The next iteration of this project moves the Kubernetes cluster to **AWS EKS**, which will make the deploy step fully automatable:

- A `KUBE_CONFIG` GitHub Secret will hold the EKS cluster's kubeconfig, base64-encoded
- The `deploy` job (already written, currently removed from the workflow) will be re-added to `cicd.yaml`, authenticating to EKS and running `kubectl set image` automatically after every successful build
- No other pipeline logic changes — the same commands that work locally will work unmodified against EKS
- The cluster will be provisioned only for testing/demo purposes and torn down (`eksctl delete cluster`) immediately after, to control cost

This section will be updated once the EKS migration is complete, along with screenshots of the fully automated end-to-end run.

## Local testing

```bash
# Build and run with Docker
docker build -t flask-k8s-cicd .
docker run -p 5000:5000 flask-k8s-cicd

# Deploy to local Kubernetes (Docker Desktop)
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl get pods

# Access the service
kubectl port-forward svc/flask-app-cicd 8080:80
curl http://localhost:8080/
```

## Proving zero-downtime under a rolling update

```bash
# In one terminal, hit the service in a loop
while true; do curl -s http://localhost:8080/ ; sleep 0.2; done

# In another terminal, trigger an update
kubectl set image deployment/flask-app flask-app=sruthidoc07/flask-k8s-cicd:latest
kubectl rollout status deployment/flask-app
```
No failed requests during the rollout confirms zero-downtime.

## What I'd improve with more time

- Complete the AWS EKS migration described above, to fully automate deployment
- Add a staging namespace and promote images staging → prod instead of deploying straight to prod
- Add Prometheus/Grafana for real rollout metrics instead of a manual curl-loop test
- Move from NodePort to an Ingress controller for a real domain-based setup
- Add a database layer with a readiness probe that checks actual connectivity, not just a static response
