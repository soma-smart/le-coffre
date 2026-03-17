# Le Coffre Helm Chart

This Helm chart deploys Le Coffre password manager on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure (for persistence)

## Installing the Chart

### Quick Start

```bash
# Add your values
helm install le-coffre ./helm/le-coffre \
  --set ingress.hosts[0].host=le-coffre.yourdomain.com \
  --set ingress.tls[0].hosts[0]=le-coffre.yourdomain.com \
  --set config.appBaseUrl=https://le-coffre.yourdomain.com \
  --set config.jwt.secretKey=$(openssl rand -base64 32)
```

### With Custom Values File

Create a `values-prod.yaml` file:

```yaml
image:
  tag: "v1.0.0"

ingress:
  hosts:
    - host: le-coffre.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: le-coffre-tls
      hosts:
        - le-coffre.yourdomain.com

config:
  appBaseUrl: "https://le-coffre.yourdomain.com"
  database:
    url: "postgresql://lecoffre:PASSWORD@postgresql:5432/lecoffre"
  jwt:
    secretKey: "YOUR_SECURE_JWT_SECRET_KEY"

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 200m
    memory: 256Mi
```

Then install:

```bash
helm install le-coffre ./helm/le-coffre -f values-prod.yaml
```

## Configuration

The following table lists the configurable parameters and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `rg.fr-par.scw.cloud/soma-smart-cr/le-coffre` |
| `image.tag` | Image tag | `""` (uses chart appVersion) |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts` | Ingress hosts configuration | See values.yaml |
| `config.environment` | Environment (development/production) | `production` |
| `config.database.url` | Database connection URL | PostgreSQL example |
| `config.jwt.secretKey` | JWT secret key (REQUIRED) | `CHANGE_ME_GENERATE_A_SECURE_KEY` |
| `config.appBaseUrl` | Application base URL | `https://le-coffre.example.com` |
| `persistence.enabled` | Enable persistence for SQLite | `false` |
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `512Mi` |

## Database Options

### Option 1: SQLite (Development Only)

```yaml
config:
  database:
    url: "sqlite:///data/le-coffre.db"

persistence:
  enabled: true
  size: 1Gi
  storageClass: "scw-bssd"
```

### Option 2: External PostgreSQL (Recommended)

```yaml
config:
  database:
    url: "postgresql://user:password@host:5432/database"
```

### Option 3: Deploy PostgreSQL with the Chart

```yaml
postgresql:
  enabled: true
  auth:
    username: lecoffre
    password: changeme
    database: lecoffre

config:
  database:
    url: "postgresql://lecoffre:changeme@le-coffre-postgresql:5432/lecoffre"
```

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

postgresql:
  primary:
    persistence:
      storageClass: "scw-bssd"
```

## Monitoring

The chart includes liveness and readiness probes that check the `/api/health` endpoint.

You can monitor the application with:

```bash
kubectl get pods -l app.kubernetes.io/name=le-coffre
kubectl logs -f deployment/le-coffre
```
