#!/bin/bash
set -e

# Le Coffre Deployment Script
# This script helps deploy Le Coffre to Kubernetes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${NAMESPACE:-le-coffre}"
RELEASE_NAME="${RELEASE_NAME:-le-coffre}"
HELM_CHART="./helm/le-coffre"
VALUES_FILE="${VALUES_FILE:-values-production.yaml}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_info "All requirements met"
}

create_namespace() {
    log_info "Creating namespace if not exists: $NAMESPACE"
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
}

create_registry_secret() {
    log_info "Creating registry secret..."

    if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ] || [ -z "$DOCKER_REGISTRY" ]; then
        log_warn "Docker credentials not set. Skipping registry secret creation."
        log_warn "Set DOCKER_USERNAME, DOCKER_PASSWORD, and DOCKER_REGISTRY environment variables."
        return
    fi

    kubectl create secret docker-registry regcred \
        --docker-server="$DOCKER_REGISTRY" \
        --docker-username="$DOCKER_USERNAME" \
        --docker-password="$DOCKER_PASSWORD" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_info "Registry secret created"
}

deploy() {
    log_info "Deploying Le Coffre..."

    if [ ! -f "$VALUES_FILE" ]; then
        log_error "Values file not found: $VALUES_FILE"
        log_info "Please create $VALUES_FILE or set VALUES_FILE environment variable"
        exit 1
    fi

    helm upgrade --install "$RELEASE_NAME" "$HELM_CHART" \
        --namespace "$NAMESPACE" \
        --values "$VALUES_FILE" \
        --wait \
        --timeout 5m

    log_info "Deployment completed"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Wait for rollout
    kubectl rollout status deployment/"$RELEASE_NAME" \
        --namespace "$NAMESPACE" \
        --timeout=5m

    # Show deployment info
    echo ""
    log_info "Deployment Status:"
    kubectl get deployment "$RELEASE_NAME" -n "$NAMESPACE"

    echo ""
    log_info "Pods:"
    kubectl get pods -l app.kubernetes.io/name=le-coffre -n "$NAMESPACE"

    echo ""
    log_info "Services:"
    kubectl get svc "$RELEASE_NAME" -n "$NAMESPACE"

    echo ""
    log_info "Ingress:"
    kubectl get ingress "$RELEASE_NAME" -n "$NAMESPACE" 2>/dev/null || log_warn "No ingress found"
}

show_logs() {
    log_info "Recent logs:"
    kubectl logs -n "$NAMESPACE" deployment/"$RELEASE_NAME" --tail=20
}

run_smoke_test() {
    log_info "Running smoke test..."

    # Get ingress host
    INGRESS_HOST=$(kubectl get ingress "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)

    if [ -z "$INGRESS_HOST" ]; then
        log_warn "No ingress host found. Skipping smoke test."
        return
    fi

    # Wait a bit for DNS propagation
    sleep 5

    # Test health endpoint
    URL="https://$INGRESS_HOST/api/health"
    log_info "Testing: $URL"

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")

    if [ "$HTTP_CODE" == "200" ]; then
        log_info "✅ Health check passed (HTTP $HTTP_CODE)"
    else
        log_warn "⚠️  Health check returned HTTP $HTTP_CODE"
        log_warn "The application might need more time to be fully ready"
    fi
}

show_help() {
    cat <<EOF
Le Coffre Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -n, --namespace NAMESPACE    Kubernetes namespace (default: le-coffre)
    -r, --release RELEASE        Helm release name (default: le-coffre)
    -f, --values FILE           Values file (default: values-production.yaml)
    --skip-verify               Skip deployment verification
    --dry-run                   Show what would be deployed without actually deploying
    -h, --help                  Show this help message

ENVIRONMENT VARIABLES:
    NAMESPACE                   Kubernetes namespace
    RELEASE_NAME               Helm release name
    VALUES_FILE                Path to values file
    DOCKER_USERNAME            Docker registry username
    DOCKER_PASSWORD            Docker registry password
    DOCKER_REGISTRY            Docker registry URL

EXAMPLES:
    # Deploy with default settings
    $0

    # Deploy to different namespace
    $0 -n production

    # Deploy with custom values file
    $0 -f values-staging.yaml

    # Deploy with registry credentials
    DOCKER_USERNAME=user DOCKER_PASSWORD=pass DOCKER_REGISTRY=registry.io $0

    # Dry run
    $0 --dry-run
EOF
}

# Parse arguments
SKIP_VERIFY=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        -f|--values)
            VALUES_FILE="$2"
            shift 2
            ;;
        --skip-verify)
            SKIP_VERIFY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "Starting Le Coffre deployment"
    log_info "Namespace: $NAMESPACE"
    log_info "Release: $RELEASE_NAME"
    log_info "Values file: $VALUES_FILE"

    check_requirements

    if [ "$DRY_RUN" = true ]; then
        log_info "DRY RUN - No changes will be made"
        helm upgrade --install "$RELEASE_NAME" "$HELM_CHART" \
            --namespace "$NAMESPACE" \
            --values "$VALUES_FILE" \
            --dry-run \
            --debug
        exit 0
    fi

    create_namespace
    create_registry_secret
    deploy

    if [ "$SKIP_VERIFY" = false ]; then
        verify_deployment
        show_logs
        run_smoke_test
    fi

    echo ""
    log_info "🚀 Deployment completed successfully!"
    log_info "To view logs: kubectl logs -f deployment/$RELEASE_NAME -n $NAMESPACE"
    log_info "To get pods: kubectl get pods -n $NAMESPACE"
}

main
