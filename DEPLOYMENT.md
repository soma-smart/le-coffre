# Deployment Guide

This document provides a quick start guide for deploying Le Coffre to Kubernetes.

## Quick Start

### 1. Prerequisites

- A Kubernetes cluster (Scaleway Kapsule recommended)
- `kubectl` configured
- `helm` installed (v3.0+)
- Docker images in Scaleway Container Registry

### 2. Prepare Configuration

Copy the example values file and customize it:

```bash
cp helm/le-coffre/values-example.yaml values-production.yaml
```

Edit `values-production.yaml` and configure:

- `image.tag`: Your Docker image tag
- `ingress.hosts[0].host`: Your domain name
- `ingress.tls[0].hosts[0]`: Your domain name
- `config.database.url`: Your database connection URL
- `config.jwt.secretKey`: Generate with `openssl rand -base64 32`
- `config.appBaseUrl`: Your application public URL

### 3. Deploy Using the Script

```bash
# Set registry credentials
export DOCKER_USERNAME="your-scw-username"
export DOCKER_PASSWORD="your-scw-password"
export DOCKER_REGISTRY="rg.fr-par.scw.cloud/soma-smart-cr"

# Deploy
./scripts/deploy.sh -f values-production.yaml
```

### 4. Deploy Using GitHub Actions

The deployment is automated via GitHub Actions. Configure these secrets in your repository:

#### Required Secrets for Scaleway

| Secret | Description | Example |
|--------|-------------|---------|
| `SCW_ACCESS_KEY` | Scaleway API access key | `SCWXXXXXXXXX` |
| `SCW_SECRET_KEY` | Scaleway API secret key | Container Registry password |
| `SCW_DEFAULT_ORGANIZATION_ID` | Scaleway organization ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `SCW_DEFAULT_PROJECT_ID` | Scaleway project ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `DOCKER_CONTAINER_REGISTRY` | Registry URL | `rg.fr-par.scw.cloud/somait-cr` |

Then push a tag to trigger deployment:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Architecture

The deployment consists of:

1. **Frontend**: Vue.js application served by nginx
2. **Backend**: FastAPI application running on uvicorn
3. **Database**: PostgreSQL (Scaleway Managed Database recommended)
4. **Ingress**: NGINX Ingress Controller with TLS via cert-manager
5. **Security**: NetworkPolicy for traffic control, PodDisruptionBudget for high availability
6. **Monitoring**: Startup, Liveness, and Readiness probes for health checking

```
┌─────────────────┐
│   Internet      │
└────────┬────────┘
         │
         │ HTTPS
         ▼
┌─────────────────┐
│ LoadBalancer    │
│ (Scaleway)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ NGINX Ingress   │
│ Controller      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────────┐
│  Le Coffre      │──────▶│   PostgreSQL     │
│  Pod            │       │   (Managed DB)   │
│  - nginx        │       └──────────────────┘
│  - uvicorn      │
└─────────────────┘
```

## Files Structure

```
le-coffre/
├── Dockerfile                          # Production multi-stage build
├── nginx.conf                          # Nginx configuration
├── helm/
│   └── le-coffre/
│       ├── Chart.yaml                  # Helm chart metadata
│       ├── values.yaml                 # Default values
│       ├── values-example.yaml         # Example production values
│       ├── README.md                   # Helm chart documentation
│       └── templates/                  # Kubernetes manifests
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           ├── configmap.yaml
│           ├── secret.yaml
│           ├── pvc.yaml
│           ├── hpa.yaml
│           └── serviceaccount.yaml
├── scripts/
│   └── deploy.sh                       # Deployment script
├── .github/
│   └── workflows/
│       ├── docker-publish.yml          # Build and push Docker images
│       └── deploy.yml                  # Deploy to Kubernetes
└── docs/
    └── kubernetes-deployment.md        # Detailed deployment guide
```

## Deployment Methods

### Method 1: Automated via GitHub Actions (Recommended)

1. Configure GitHub secrets (see above)
2. Push a git tag: `git tag v1.0.0 && git push origin v1.0.0`
3. GitHub Actions will:
   - Build Docker image
   - Push to Scaleway Container Registry
   - Deploy to Kubernetes with Helm

### Method 2: Manual with Script

```bash
./scripts/deploy.sh -f values-production.yaml
```

### Method 3: Manual with Helm

```bash
# Create namespace
kubectl create namespace le-coffre

# Create registry secret
kubectl create secret docker-registry regcred \
  --docker-server=rg.fr-par.scw.cloud/soma-smart-cr \
  --docker-username=<username> \
  --docker-password=<password> \
  --namespace=le-coffre

# Deploy
helm install le-coffre ./helm/le-coffre \
  --namespace le-coffre \
  --values values-production.yaml
```

## Environment Variables

The application uses these environment variables (configured via ConfigMap and Secret):

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | Yes | - |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Yes | - |
| `JWT_ALGORITHM` | JWT signing algorithm | No | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRATION_MINUTES` | Access token TTL | No | `15` |
| `JWT_REFRESH_TOKEN_EXPIRATION_DAYS` | Refresh token TTL | No | `7` |
| `APP_BASE_URL` | Application base URL | Yes | - |
| `ENVIRONMENT` | Environment (production/development) | No | `production` |

## Database Setup

### Scaleway Managed PostgreSQL (Recommended)

1. Create a PostgreSQL instance in Scaleway Console
2. Create a database: `CREATE DATABASE lecoffre;`
3. Get connection URL from Scaleway Console
4. Set in `config.database.url`:
   ```
   postgresql://username:password@host.pg.svc.scw.cloud:5432/lecoffre
   ```

### In-Cluster PostgreSQL

Enable in `values.yaml`:

```yaml
postgresql:
  enabled: true
  auth:
    username: lecoffre
    password: changeme
    database: lecoffre
```

## Monitoring

### Check Application Status

```bash
# Pods
kubectl get pods -n le-coffre

# Logs
kubectl logs -f deployment/le-coffre -n le-coffre

# Health check
curl https://your-domain.com/api/health
```

### Resource Usage

```bash
kubectl top pods -n le-coffre
```

## Troubleshooting

See [docs/kubernetes-deployment.md](docs/kubernetes-deployment.md) for detailed troubleshooting guide.

### Common Issues

1. **Pods not starting**: Check logs with `kubectl logs <pod-name> -n le-coffre`
2. **Image pull errors**: Verify registry credentials in `regcred` secret
3. **Database connection**: Verify `DATABASE_URL` is correct
4. **TLS certificate**: Check cert-manager logs and certificate status

## Scaling

### Manual Scaling

```bash
kubectl scale deployment/le-coffre --replicas=3 -n le-coffre
```

### Auto-Scaling

Enable in values:

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
```

## Backup

### Database Backup

```bash
# For Scaleway Managed DB: Use automatic backups in Scaleway Console

# For in-cluster PostgreSQL
kubectl exec -it postgresql-0 -n le-coffre -- \
  pg_dump -U lecoffre lecoffre > backup.sql
```

## Updates

### Update Application

1. Build new Docker image with new tag
2. Update `image.tag` in values file
3. Deploy:
   ```bash
   ./scripts/deploy.sh -f values-production.yaml
   ```

### Rollback

```bash
helm rollback le-coffre -n le-coffre
```

## Security Checklist

- [ ] Generated secure JWT secret key
- [ ] Using HTTPS/TLS (cert-manager configured)
- [ ] Using PostgreSQL (not SQLite) in production
- [ ] Registry credentials secured in Kubernetes Secret
- [ ] Database credentials secured (not in values file)
- [ ] Resource limits configured
- [ ] NetworkPolicy enabled for traffic control
- [ ] PodDisruptionBudget configured for high availability
- [ ] Security headers configured in Ingress (X-Frame-Options, CSP, etc.)
- [ ] OWASP ModSecurity rules enabled in Ingress
- [ ] TLS 1.3 only enforced
- [ ] Pod security context configured (non-root user)
- [ ] Read-only root filesystem (where possible)
- [ ] Regular database backups enabled

## Makefile Commands

The project includes a comprehensive Makefile for common operations:

```bash
# Build and push Docker image
make build                    # Build Docker image
make build-multiplatform      # Build for linux/amd64 and linux/arm64
make push                     # Push to registry
make build-push               # Build and push

# Deployment
make deploy                   # Deploy to Kubernetes
make deploy-staging           # Deploy to staging environment
make deploy-production        # Deploy to production environment
make rollback                 # Rollback to previous release

# Helm operations
make helm-lint                # Lint Helm chart
make helm-template            # Render templates
make helm-dry-run             # Dry run deployment
make helm-diff                # Show diff between current and new

# Monitoring
make status                   # Show deployment status
make logs                     # Show application logs
make health                   # Check application health
make top                      # Show resource usage
make events                   # Show recent events

# Utilities
make generate-jwt-secret      # Generate secure JWT key
make namespace-create         # Create namespace
make secrets-create           # Create secrets (interactive)
make security-scan            # Run Trivy security scan
make pre-commit               # Run pre-commit hooks

# Maintenance
make scale REPLICAS=3         # Scale deployment
make restart                  # Restart deployment
make clean                    # Remove deployment
```

## Support

For detailed documentation, see:
- [Helm Chart README](helm/le-coffre/README.md)
- [Kubernetes Deployment Guide](docs/kubernetes-deployment.md)
- [Main README](README.md)
