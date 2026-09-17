# Kubernetes Deployment Guide

This directory contains production-ready Kubernetes manifests for deploying the FastAPI backend of [`js-chat-telegram-widget`](https://github.com/timothechauvet/js-chat-telegram-widget).

---

## 🏗️ Architecture & Key Considerations

- **Container Image**: Hosted on GitHub Container Registry:
  `ghcr.io/timothechauvet/js-chat-telegram-widget-backend:latest`
- **Security & Least Privilege**: The container runs under non-root UID/GID `10001` (`appuser`). The pod manifest enforces `runAsNonRoot: true` and `fsGroup: 10001`.
- **Persistent Storage (SQLite & Media)**: Data (`chat.db` and uploaded attachments) is stored in `/data` backed by a `PersistentVolumeClaim` with `ReadWriteOnce` access mode.
- **Deployment Strategy**: Set to `type: Recreate` so that during updates the existing pod releases the volume lock before the new pod attaches to it.
- **Bi-Directional Telegram Webhook**: Telegram pushes admin replies and auth commands over HTTPS (`POST /api/v1/telegram-webhook`). An Ingress controller with valid TLS (e.g., via cert-manager and Let's Encrypt) is required.

---

## 📁 Manifest Structure

| File | Resource | Description |
|---|---|---|
| [`namespace.yaml`](./namespace.yaml) | `Namespace` | Dedicated `telegram-chat` namespace |
| [`configmap.yaml`](./configmap.yaml) | `ConfigMap` | Non-sensitive runtime variables (`CORS`, retention, limits) |
| [`secret.example.yaml`](./secret.example.yaml) | `Secret` | Template for Telegram bot tokens and authentication secrets |
| [`pvc.yaml`](./pvc.yaml) | `PersistentVolumeClaim` | 5Gi persistent disk mounted at `/data` |
| [`deployment.yaml`](./deployment.yaml) | `Deployment` | Single replica pod with health probes and resource limits |
| [`service.yaml`](./service.yaml) | `Service` | Internal `ClusterIP` on port 80 routing to port 8000 |
| [`ingress.yaml`](./ingress.yaml) | `Ingress` | NGINX Ingress rule with TLS and 25MB body size limit |
| [`kustomization.yaml`](./kustomization.yaml) | `Kustomization` | Bundle all manifests for one-command deployment |

---

## 🚀 Step-by-Step Deployment

### Step 1: Container Image Verification
The backend Docker image is automatically built and published to GHCR upon creating a release tag (e.g. `v1.0.0`) via `.github/workflows/publish-backend.yml`:

```bash
ghcr.io/timothechauvet/js-chat-telegram-widget-backend:latest
```

To build and push manually:
```bash
docker build -t ghcr.io/timothechauvet/js-chat-telegram-widget-backend:latest packages/backend
docker push ghcr.io/timothechauvet/js-chat-telegram-widget-backend:latest
```

If your GHCR package is private, create a pull secret in the namespace:
```bash
kubectl create namespace telegram-chat
kubectl create secret docker-registry ghcr-secret \
  --namespace telegram-chat \
  --docker-server=ghcr.io \
  --docker-username=<GITHUB_USERNAME> \
  --docker-password=<GITHUB_PAT_TOKEN>
```
*(And add `imagePullSecrets: [{ name: ghcr-secret }]` to `deployment.yaml`).*

---

### Step 2: Create Secrets
Generate strong random strings for the webhook and admin authentication secrets, then create the Kubernetes Secret:

```bash
kubectl create namespace telegram-chat

kubectl create secret generic telegram-chat-backend-secret \
  --namespace telegram-chat \
  --from-literal=TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ" \
  --from-literal=TELEGRAM_WEBHOOK_SECRET="$(openssl rand -hex 24)" \
  --from-literal=TELEGRAM_AUTH_SECRET="$(openssl rand -hex 16)" \
  --from-literal=BACKEND_SECRET_KEY="$(openssl rand -hex 32)"
```

---

### Step 3: Configure Ingress & Domain
1. Edit [`k8s/ingress.yaml`](./ingress.yaml) and replace `chat.yourdomain.com` with your real DNS record.
2. Ensure your DNS points to your Kubernetes Ingress controller's external IP.
3. Edit [`k8s/configmap.yaml`](./configmap.yaml) if you need to restrict `CORS_ALLOW_ORIGINS` to specific domains (e.g. `https://mywebsite.com`).

---

### Step 4: Deploy Manifests
Deploy the complete stack using Kustomize:

```bash
kubectl apply -k k8s/
```

Verify that all resources are healthy:
```bash
# Check pod status
kubectl get pods -n telegram-chat

# Check logs
kubectl logs -n telegram-chat -l app.kubernetes.io/name=telegram-chat-backend -f

# Verify ingress status
kubectl get ingress -n telegram-chat
```

Test the health endpoint from outside the cluster:
```bash
curl https://chat.yourdomain.com/health
# Expected output: {"status":"healthy"}
```

---

### Step 5: Configure Telegram Webhook
Once the domain resolves with valid HTTPS, register the webhook with Telegram Bot API:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://chat.yourdomain.com/api/v1/telegram-webhook",
       "secret_token": "<TELEGRAM_WEBHOOK_SECRET>"
     }'
```

Verify webhook registration:
```bash
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

---

## 🛠️ Operational Guide

### Database & Media Backups
To take a snapshot backup of the live SQLite database without stopping the pod:
```bash
POD_NAME=$(kubectl get pod -n telegram-chat -l app.kubernetes.io/name=telegram-chat-backend -o jsonpath="{.items[0].metadata.name}")

# Safely copy database
kubectl exec -n telegram-chat "$POD_NAME" -- sqlite3 /data/chat.db ".backup /data/chat_backup.sqlite"
kubectl cp "telegram-chat/${POD_NAME}:/data/chat_backup.sqlite" ./chat_backup.sqlite
```

### Scaling & Horizontal Pod Autoscaling (HPA)
> [!NOTE]
> The backend currently uses local file persistence for media and an embedded SQLite database (`/data/chat.db`). Because SQLite requires exclusive write locks, running multiple replicas concurrently on a shared file system is not recommended without transitioning to PostgreSQL or MySQL. Keep `replicas: 1` for standard deployments.
