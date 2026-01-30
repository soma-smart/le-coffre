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

### 4. Deploy Using GitHub Actions (Automated CI/CD)

The deployment is fully automated via GitHub Actions with a streamlined CI/CD pipeline.

#### CI/CD Pipeline Overview

The pipeline consists of two main workflows that run automatically:

1. **docker-publish.yml**: Builds and publishes Docker images
   - Triggers on: `main` branch and version tags (`v*.*.*`)
   - Produces images with consistent tags: `main-<sha>` or `v1.0.0` for releases
   - Runs Trivy security scanning on all images
   - Outputs: `image_tag`, `sha_short`, `branch_name`

2. **deploy.yml**: Deploys to production on Kubernetes
   - Automatically triggered after successful docker-publish on `main` branch
   - Deploys to `le-coffre` namespace (production environment)
   - Uses Helm with atomic rollback capability
   - Runs health checks and verification
   - Provides detailed deployment summaries

#### Required GitHub Secrets

Configure these secrets in your repository settings:

| Secret | Description | Example |
|--------|-------------|---------|
| `SCW_ACCESS_KEY` | Scaleway API access key | `SCWXXXXXXXXX` |
| `SCW_SECRET_KEY` | Scaleway API secret key | Container Registry password |
| `SCW_DEFAULT_ORGANIZATION_ID` | Scaleway organization ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `SCW_DEFAULT_PROJECT_ID` | Scaleway project ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `DOCKER_CONTAINER_REGISTRY` | Registry URL | `rg.fr-par.scw.cloud/somait-cr` |

#### Required GitHub Environment

Create a `production` environment in your GitHub repository settings for deployment protection and tracking.

#### Deployment Triggers

The pipeline deploys automatically in these scenarios:

**1. Deploy from main (Standard Production)**
```bash
git checkout main
git push origin main
# → Triggers: docker-publish → deploy → production
```

**2. Deploy from version tag (Release)**
```bash
git tag v1.0.0
git push origin v1.0.0
# → Triggers: docker-publish → deploy → production + GitHub Release
```

**3. Manual Deployment (Specific Image)**
- Go to Actions → Deploy to Kubernetes → Run workflow
- Specify the image tag (e.g., `main-abc1234`, `v1.0.0`)
- Click "Run workflow"

#### Image Tagging Strategy

The pipeline uses a consistent tagging strategy:

- **main branch**: `main-<sha7>` + `latest`
- **Version tags**: `v1.0.0` + `1.0` + `latest`

Example: Pushing to `main` with SHA `abc1234` creates:
- `rg.fr-par.scw.cloud/somait-cr/le-coffre:main-abc1234`
- `rg.fr-par.scw.cloud/somait-cr/le-coffre:latest`

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
2. Create the `production` environment in GitHub repository settings
3. Deploy using one of these methods:

**For standard deployments:**
```bash
git push origin main
```

**For releases:**
```bash
git tag v1.0.0
git push origin v1.0.0
```

4. GitHub Actions will automatically:
   - Build Docker image with appropriate tags
   - Run Trivy security scan
   - Push to Scaleway Container Registry
   - Deploy to Kubernetes with Helm (atomic with rollback on failure)
   - Run health checks
   - Provide deployment summary

5. Monitor the deployment in the Actions tab on GitHub

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

The deployment uses Helm's `--atomic` flag, which automatically rolls back on failure. For manual rollback:

**Quick Rollback (to previous version):**
```bash
helm rollback le-coffre -n le-coffre
```

**Rollback to Specific Revision:**
```bash
# View deployment history
helm history le-coffre -n le-coffre

# Rollback to specific revision
helm rollback le-coffre <revision-number> -n le-coffre
```

**Rollback via GitHub Actions:**
1. Go to Actions → Deploy to Kubernetes → Run workflow
2. Enter the previous image tag (e.g., `main-abc1234`)
3. Click "Run workflow"

**View Current Deployment:**
```bash
# Check current image tag
kubectl get deployment le-coffre -n le-coffre -o jsonpath='{.spec.template.spec.containers[0].image}'

# Check deployment labels (shows source branch and SHA)
kubectl get deployment le-coffre -n le-coffre -o jsonpath='{.spec.template.metadata.labels}'
```

## CI/CD Pipeline Details

### Workflow Files

**`.github/workflows/docker-publish.yml`**
- Builds Docker images on push to `main`, `feature/add-ci-cd`, or version tags
- Creates consistent image tags based on branch and SHA
- Runs Trivy security scanning on all images
- Uploads security results to GitHub Security tab
- Outputs metadata for the deploy workflow

**`.github/workflows/deploy.yml`**
- Automatically triggered after successful docker-publish workflow
- Can be manually triggered with custom image tag
- Determines correct image tag from workflow_run context
- Deploys to production environment on Kubernetes
- Adds deployment labels for traceability (branch, SHA, timestamp)
- Runs comprehensive health checks
- Provides detailed deployment summaries and logs on failure
- Uses Helm's atomic mode for automatic rollback on failure

**`.github/workflows/CI.yml`**
- Runs tests and linting on PRs and main branch
- Validates code quality before deployment

**`.github/workflows/generate-publish-release.yaml`**
- Creates GitHub releases when version tags are pushed
- Automatically generates release notes

### Deployment Verification

After deployment, the pipeline automatically verifies:

1. **Rollout Status**: Waits for pods to be ready (5 min timeout)
2. **Pod Status**: Checks all pods are running
3. **Service Status**: Verifies service endpoints
4. **Ingress Status**: Confirms ingress configuration
5. **Health Check**: Tests application endpoint (30 retries, 10s interval)

If any verification fails:
- Detailed logs are displayed (last 50 lines)
- Pod status and descriptions are shown
- Deployment is rolled back automatically (via `--atomic`)

### Deployment Traceability

Every deployment includes metadata labels:

```yaml
podLabels:
  deployed-from-branch: "feature/add-ci-cd"  # Source branch
  deployed-sha: "abc1234"                     # Short commit SHA
  deployed-at: "1706543210"                   # Unix timestamp
```

View deployment metadata:
```bash
kubectl get deployment le-coffre -n le-coffre -o jsonpath='{.spec.template.metadata.labels}' | jq
```

### Health Checks

The application includes comprehensive health probes:

**Startup Probe** (startup only):
- Path: `/api/health`
- Failure threshold: 30
- Period: 10 seconds
- Allows up to 5 minutes for startup

**Liveness Probe** (running state):
- Path: `/api/health`
- Initial delay: 30 seconds
- Period: 10 seconds
- Failure threshold: 3

**Readiness Probe** (traffic readiness):
- Path: `/api/health`
- Initial delay: 10 seconds
- Period: 5 seconds
- Failure threshold: 3

### Deployment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Push to main/feature/add-ci-cd or Create Tag v*.*.*           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │  docker-publish.yml           │
         │  - Build Docker image         │
         │  - Tag: <branch>-<sha>        │
         │  - Run Trivy scan             │
         │  - Push to registry           │
         │  - Output: image_tag          │
         └───────────────┬───────────────┘
                         │
                         │ (workflow_run trigger)
                         ▼
         ┌───────────────────────────────┐
         │  deploy.yml                   │
         │  - Determine image tag        │
         │  - Connect to K8s cluster     │
         │  - Deploy with Helm           │
         │  - Add traceability labels    │
         │  - Verify deployment          │
         │  - Run health checks          │
         │  - Generate summary           │
         └───────────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Production      │
              │  (le-coffre)     │
              │  namespace       │
              └──────────────────┘
```

### Testing the Pipeline

The CI/CD pipeline runs automatically on the `main` branch:

1. **Push to main triggers the pipeline:**
   ```bash
   git checkout main
   git push origin main
   ```

2. **Monitor the workflow:**
   - Go to GitHub Actions tab
   - Watch docker-publish workflow complete
   - Watch deploy workflow auto-trigger
   - Check deployment summary

3. **Verify deployment:**
   ```bash
   # Check pod status
   kubectl get pods -n le-coffre

   # Check deployment labels
   kubectl get deployment le-coffre -n le-coffre -o yaml | grep -A 5 "deployed-"

   # Test application
   curl https://le-coffre.soma-smart.cloud/api/health
   ```

### Troubleshooting CI/CD

**Workflow not triggering:**
- Ensure workflow files exist on the target branch
- Check workflow permissions in repository settings
- Verify `workflow_run` branches match in deploy.yml

**Image tag mismatch:**
- Check docker-publish outputs in workflow logs
- Verify image exists in registry: `docker pull <registry>/<image>:<tag>`
- Review deploy workflow "Determine Image Tag" step

**Deployment fails:**
- Check Helm upgrade output for errors
- Review pod logs: `kubectl logs -n le-coffre -l app.kubernetes.io/name=le-coffre --tail=100`
- Check resource constraints: `kubectl describe pod <pod-name> -n le-coffre`
- Verify secrets and configmaps are correct

**Health check fails:**
- Check ingress configuration: `kubectl get ingress -n le-coffre`
- Verify DNS points to load balancer
- Check TLS certificate: `kubectl get certificate -n le-coffre`
- Review application logs for errors

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
