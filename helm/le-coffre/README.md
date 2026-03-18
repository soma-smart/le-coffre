# Le Coffre Helm Chart

This Helm chart deploys Le Coffre password manager on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+ (1.23+ if autoscaling or PodDisruptionBudget is enabled)
- Helm 3.0+
- PV provisioner support in the underlying infrastructure (for persistence)

## Installing the Chart

### Quick Start

Before installing, create the two required secrets:

```bash
# 1. JWT secret
kubectl create secret generic le-coffre \
  --from-literal=JWT_SECRET_KEY="$(openssl rand -base64 32)" \
  -n le-coffre

# 2. Database URL
kubectl create secret generic le-coffre-db \
  --from-literal=DATABASE_URL="postgresql://user:password@db-host:5432/lecoffre?sslmode=require" \
  -n le-coffre
```

Then install:

```bash
helm install le-coffre ./helm/le-coffre \
  --set config.jwt.existingSecretName=le-coffre \
  --set config.database.existingSecretName=le-coffre-db \
  --set ingress.enabled=true \
  --set "ingress.hosts[0].host=le-coffre.yourdomain.com" \
  --set "ingress.tls[0].secretName=le-coffre-tls" \
  --set "ingress.tls[0].hosts[0]=le-coffre.yourdomain.com" \
  --set config.appBaseUrl=https://le-coffre.yourdomain.com \
  -n le-coffre
```

### With Custom Values File

Copy `values-example.yaml` and adapt it for your environment:

```bash
cp helm/le-coffre/values-example.yaml values-prod.yaml
# Edit values-prod.yaml, then:
helm upgrade --install le-coffre ./helm/le-coffre -f values-prod.yaml -n le-coffre
```

## Configuration

The following table lists the main configurable parameters. See `values.yaml` for the full list with defaults.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.replicaCount` | Frontend replica count | `1` |
| `frontend.image.tag` | Frontend image tag | `""` (uses chart appVersion) |
| `frontend.image.pullPolicy` | Frontend image pull policy | `IfNotPresent` |
| `backend.replicaCount` | Backend replica count | `1` |
| `backend.image.tag` | Backend image tag | `""` (uses chart appVersion) |
| `backend.image.pullPolicy` | Backend image pull policy | `IfNotPresent` |
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts` | Ingress hosts configuration | See values.yaml |
| `config.environment` | Environment (development/production) | `production` |
| `config.jwt.existingSecretName` | Name of pre-existing secret containing `JWT_SECRET_KEY` | `""` (required) |
| `config.jwt.secretKey` | Let Helm manage the JWT secret (not recommended for production) | `""` |
| `config.database.existingSecretName` | Name of pre-existing secret containing `DATABASE_URL` | `"le-coffre-db"` |
| `config.appBaseUrl` | Application base URL (required) | `""` |
| `persistence.enabled` | Enable persistence for SQLite | `false` |
| `backend.resources.limits.cpu` | Backend CPU limit | `500m` |
| `backend.resources.limits.memory` | Backend memory limit | `512Mi` |

## Database Options

### Option 1: External PostgreSQL (Recommended)

Create the database secret before deploying:

```bash
kubectl create secret generic le-coffre-db \
  --from-literal=DATABASE_URL="postgresql://user:password@host:5432/lecoffre?sslmode=require" \
  -n le-coffre
```

Then reference it in your values:

```yaml
config:
  database:
    existingSecretName: "le-coffre-db"
```

### Option 2: SQLite (Development Only)

```bash
kubectl create secret generic le-coffre-db \
  --from-literal=DATABASE_URL="sqlite:////data/le-coffre.db" \
  -n le-coffre
```

```yaml
config:
  database:
    existingSecretName: "le-coffre-db"

persistence:
  enabled: true
  size: 1Gi
  storageClass: "standard"
```

> **Note:** SQLite with `replicaCount > 1` is not supported (ReadWriteOnce PVC).

## Upgrading

```bash
helm upgrade le-coffre ./helm/le-coffre -f values-prod.yaml
```

## Uninstalling

```bash
helm uninstall le-coffre
```

## Security Considerations

1. Always generate a secure JWT secret key:
   ```bash
   openssl rand -base64 32
   ```

2. Use PostgreSQL in production (not SQLite)

3. Enable TLS/HTTPS via ingress

4. Store secrets securely (consider using sealed-secrets or external-secrets)

5. Review and adjust resource limits based on your needs

6. Enable network policies to restrict pod communication

## Scaleway Specific Configuration

For Scaleway Kubernetes (Kapsule):

```yaml
ingress:
  className: "nginx"

persistence:
  storageClass: "scw-bssd"  # or "scw-sbv" for slower, cheaper storage
```

## Monitoring

The chart configures liveness and readiness probes on `/api/health` (backend) and `/` (frontend) by default.

You can monitor the application with:

```bash
kubectl get pods -l app.kubernetes.io/name=le-coffre
kubectl logs -f deployment/le-coffre
```
