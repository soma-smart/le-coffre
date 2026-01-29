.PHONY: help build push deploy deploy-staging deploy-production rollback logs status clean test

# Configuration
REGISTRY ?= rg.fr-par.scw.cloud/somait-cr
IMAGE_NAME ?= le-coffre
VERSION ?= $(shell git describe --tags --always --dirty)
NAMESPACE ?= le-coffre
HELM_RELEASE ?= le-coffre
HELM_CHART ?= ./helm/le-coffre

# Colors for output
YELLOW := \033[1;33m
GREEN := \033[1;32m
NC := \033[0m

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker image
	@echo "$(YELLOW)Building Docker image: $(REGISTRY)/$(IMAGE_NAME):$(VERSION)$(NC)"
	docker build -t $(REGISTRY)/$(IMAGE_NAME):$(VERSION) .
	docker tag $(REGISTRY)/$(IMAGE_NAME):$(VERSION) $(REGISTRY)/$(IMAGE_NAME):latest
	@echo "$(GREEN)✓ Build completed$(NC)"

build-multiplatform: ## Build multi-platform Docker image (linux/amd64,linux/arm64)
	@echo "$(YELLOW)Building multi-platform Docker image: $(REGISTRY)/$(IMAGE_NAME):$(VERSION)$(NC)"
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t $(REGISTRY)/$(IMAGE_NAME):$(VERSION) \
		-t $(REGISTRY)/$(IMAGE_NAME):latest \
		--push \
		.
	@echo "$(GREEN)✓ Multi-platform build completed and pushed$(NC)"

push: ## Push Docker image to registry
	@echo "Pushing Docker image: $(REGISTRY)/$(IMAGE_NAME):$(VERSION)"
	docker push $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	docker push $(REGISTRY)/$(IMAGE_NAME):latest

build-push: build push ## Build and push Docker image

deploy: ## Deploy to Kubernetes (default namespace)
	@echo "Deploying to namespace: $(NAMESPACE)"
	@if [ ! -f values-production.yaml ]; then \
		echo "Error: values-production.yaml not found"; \
		echo "Copy helm/le-coffre/values-example.yaml to values-production.yaml and configure it"; \
		exit 1; \
	fi
	./scripts/deploy.sh -f values-production.yaml -n $(NAMESPACE)

deploy-staging: ## Deploy to staging environment
	$(MAKE) deploy NAMESPACE=le-coffre-staging

deploy-production: ## Deploy to production environment
	$(MAKE) deploy NAMESPACE=le-coffre-production

rollback: ## Rollback to previous Helm release
	@echo "Rolling back release: $(HELM_RELEASE) in namespace: $(NAMESPACE)"
	helm rollback $(HELM_RELEASE) -n $(NAMESPACE)

logs: ## Show application logs
	kubectl logs -f deployment/$(HELM_RELEASE) -n $(NAMESPACE)

status: ## Show deployment status
	@echo "=== Deployment ==="
	kubectl get deployment $(HELM_RELEASE) -n $(NAMESPACE)
	@echo ""
	@echo "=== Pods ==="
	kubectl get pods -l app.kubernetes.io/name=le-coffre -n $(NAMESPACE)
	@echo ""
	@echo "=== Services ==="
	kubectl get svc $(HELM_RELEASE) -n $(NAMESPACE)
	@echo ""
	@echo "=== Ingress ==="
	kubectl get ingress $(HELM_RELEASE) -n $(NAMESPACE)

health: ## Check application health
	@INGRESS_HOST=$$(kubectl get ingress $(HELM_RELEASE) -n $(NAMESPACE) -o jsonpath='{.spec.rules[0].host}' 2>/dev/null); \
	if [ -z "$$INGRESS_HOST" ]; then \
		echo "No ingress found"; \
		exit 1; \
	fi; \
	echo "Checking health at: https://$$INGRESS_HOST/api/health"; \
	curl -f https://$$INGRESS_HOST/api/health || exit 1

describe-pod: ## Describe pods
	kubectl describe pods -l app.kubernetes.io/name=le-coffre -n $(NAMESPACE)

shell: ## Open shell in running pod
	kubectl exec -it deployment/$(HELM_RELEASE) -n $(NAMESPACE) -- /bin/bash

port-forward: ## Port forward to local machine (8080)
	kubectl port-forward deployment/$(HELM_RELEASE) 8080:8080 -n $(NAMESPACE)

clean: ## Remove deployment
	helm uninstall $(HELM_RELEASE) -n $(NAMESPACE)

helm-lint: ## Lint Helm chart
	@echo "$(YELLOW)Linting Helm chart...$(NC)"
	helm lint $(HELM_CHART)
	@echo "$(GREEN)✓ Helm lint passed$(NC)"

helm-template: ## Render Helm templates
	@echo "$(YELLOW)Rendering Helm templates...$(NC)"
	helm template $(HELM_RELEASE) $(HELM_CHART) -f values-production.yaml

helm-dry-run: ## Dry run Helm deployment
	@echo "$(YELLOW)Running Helm dry-run...$(NC)"
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		-f values-production.yaml \
		-n $(NAMESPACE) \
		--dry-run --debug
	@echo "$(GREEN)✓ Dry run completed$(NC)"

helm-diff: ## Show diff between current and new Helm release
	@echo "$(YELLOW)Showing Helm diff...$(NC)"
	helm diff upgrade $(HELM_RELEASE) $(HELM_CHART) \
		-f values-production.yaml \
		-n $(NAMESPACE) || true

test: ## Run tests locally
	@echo "Running frontend tests..."
	cd frontend && bun run test:unit
	@echo "Running backend tests..."
	cd server && uv run pytest -n auto

docker-login: ## Login to Docker registry
	@echo "Logging in to $(REGISTRY)"
	docker login $(REGISTRY)

generate-jwt-secret: ## Generate a secure JWT secret key
	@echo "Generated JWT Secret Key:"
	@openssl rand -base64 32

update-image: ## Update deployment with new image version
	@if [ -z "$(TAG)" ]; then \
		echo "Error: TAG is required. Usage: make update-image TAG=v1.0.0"; \
		exit 1; \
	fi
	kubectl set image deployment/$(HELM_RELEASE) \
		le-coffre=$(REGISTRY)/$(IMAGE_NAME):$(TAG) \
		-n $(NAMESPACE)
	kubectl rollout status deployment/$(HELM_RELEASE) -n $(NAMESPACE)

scale: ## Scale deployment (usage: make scale REPLICAS=3)
	@if [ -z "$(REPLICAS)" ]; then \
		echo "Error: REPLICAS is required. Usage: make scale REPLICAS=3"; \
		exit 1; \
	fi
	kubectl scale deployment/$(HELM_RELEASE) --replicas=$(REPLICAS) -n $(NAMESPACE)

restart: ## Restart deployment
	kubectl rollout restart deployment/$(HELM_RELEASE) -n $(NAMESPACE)

events: ## Show recent events
	kubectl get events -n $(NAMESPACE) --sort-by='.lastTimestamp' | tail -20

top: ## Show resource usage
	kubectl top pods -n $(NAMESPACE)

backup-db: ## Backup database (for in-cluster PostgreSQL)
	@echo "Backing up database..."
	kubectl exec -it postgresql-0 -n $(NAMESPACE) -- \
		pg_dump -U lecoffre lecoffre > backup-$$(date +%Y%m%d-%H%M%S).sql
	@echo "Backup completed: backup-$$(date +%Y%m%d-%H%M%S).sql"

create-values: ## Create values-production.yaml from example
	@if [ -f values-production.yaml ]; then \
		echo "Error: values-production.yaml already exists"; \
		exit 1; \
	fi
	cp helm/le-coffre/values-example.yaml values-production.yaml
	@echo "$(GREEN)Created values-production.yaml from example$(NC)"
	@echo "$(YELLOW)Please edit values-production.yaml before deploying$(NC)"

pre-commit: ## Run pre-commit hooks
	@if [ -f .pre-commit-config.yaml ]; then \
		echo "$(YELLOW)Running pre-commit hooks...$(NC)"; \
		pre-commit run --all-files; \
		echo "$(GREEN)✓ Pre-commit checks passed$(NC)"; \
	else \
		echo "$(YELLOW)No .pre-commit-config.yaml found$(NC)"; \
	fi

security-scan: ## Run security scan on Docker image
	@echo "$(YELLOW)Running security scan...$(NC)"
	trivy image $(REGISTRY)/$(IMAGE_NAME):$(VERSION) || true
	@echo "$(GREEN)✓ Security scan completed$(NC)"

install-tools: ## Install required tools (helm, kubectl, etc.)
	@echo "$(YELLOW)Checking required tools...$(NC)"
	@command -v helm >/dev/null 2>&1 || { echo "helm not found. Installing..."; brew install helm; }
	@command -v kubectl >/dev/null 2>&1 || { echo "kubectl not found. Installing..."; brew install kubectl; }
	@command -v docker >/dev/null 2>&1 || { echo "docker not found. Please install Docker Desktop"; exit 1; }
	@echo "$(GREEN)✓ All required tools are installed$(NC)"

namespace-create: ## Create namespace if it doesn't exist
	@echo "$(YELLOW)Creating namespace $(NAMESPACE) if it doesn't exist...$(NC)"
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	@echo "$(GREEN)✓ Namespace $(NAMESPACE) ready$(NC)"

secrets-create: ## Create secrets in namespace (interactive)
	@echo "$(YELLOW)Creating secrets...$(NC)"
	@read -p "Enter JWT Secret Key (or press Enter to generate): " jwt_secret; \
	if [ -z "$$jwt_secret" ]; then \
		jwt_secret=$$(openssl rand -base64 32); \
		echo "Generated JWT Secret: $$jwt_secret"; \
	fi; \
	kubectl create secret generic le-coffre-secrets \
		--from-literal=JWT_SECRET_KEY=$$jwt_secret \
		-n $(NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "$(GREEN)✓ Secrets created$(NC)"
