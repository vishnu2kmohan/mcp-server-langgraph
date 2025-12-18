# ==============================================================================
# Deployment
# ==============================================================================

deploy-dev:
	@echo "Deploying to development environment..."
	kubectl apply -k deployments/overlays/dev
	@echo "Waiting for rollout..."
	kubectl rollout status deployment/dev-langgraph-agent -n langgraph-agent-dev --timeout=5m
	@echo "Development deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent-dev"
	@echo "  kubectl logs -f deployment/dev-langgraph-agent -n langgraph-agent-dev"

deploy-staging:
	@echo "Deploying to staging environment..."
	kubectl apply -k deployments/overlays/staging
	@echo "Waiting for rollout..."
	kubectl rollout status deployment/staging-langgraph-agent -n langgraph-agent-staging --timeout=5m
	@echo "Staging deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent-staging"
	@echo "  kubectl logs -f deployment/staging-langgraph-agent -n langgraph-agent-staging"

deploy-production:
	@echo "WARNING: Deploying to PRODUCTION environment"
	@echo "Press Ctrl+C within 10 seconds to cancel..."
	@sleep 10
	@echo "Deploying to production with Helm..."
	helm upgrade --install langgraph-agent deployments/helm/mcp-server-langgraph \
		--namespace langgraph-agent \
		--create-namespace \
		--wait \
		--timeout 10m
	@echo "Production deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent"
	@echo "  kubectl logs -f deployment/langgraph-agent -n langgraph-agent"

deploy-rollback-dev:
	@echo "Rolling back development deployment..."
	kubectl rollout undo deployment/dev-langgraph-agent -n langgraph-agent-dev
	kubectl rollout status deployment/dev-langgraph-agent -n langgraph-agent-dev
	@echo "Development rollback complete"

deploy-rollback-staging:
	@echo "Rolling back staging deployment..."
	kubectl rollout undo deployment/staging-langgraph-agent -n langgraph-agent-staging
	kubectl rollout status deployment/staging-langgraph-agent -n langgraph-agent-staging
	@echo "Staging rollback complete"

deploy-rollback-production:
	@echo "WARNING: Rolling back PRODUCTION deployment"
	@echo "Press Ctrl+C within 10 seconds to cancel..."
	@sleep 10
	helm rollback langgraph-agent -n langgraph-agent
	@echo "Production rollback complete"

# Deployment testing
test-k8s-deployment:
	@echo "Running Kubernetes deployment tests..."
	bash scripts/deployment/test_k8s_deployment.sh

test-helm-deployment:
	@echo "Running Helm deployment tests..."
	bash scripts/deployment/test_helm_deployment.sh

# ==============================================================================
# GKE Preview Deployment
# ==============================================================================

preflight-preview-gke:
	@echo "Preview GKE Pre-Flight Checks"
	@echo ""
	@echo "Validating Kustomize overlay..."
	@kubectl kustomize deployments/overlays/preview-gke > /dev/null && echo "  Kustomize overlay valid" || (echo "  Kustomize overlay invalid" && exit 1)
	@echo ""
	@echo "Checking GKE cluster access..."
	@kubectl cluster-info > /dev/null 2>&1 && echo "  kubectl connected to cluster" || (echo "  kubectl not connected" && exit 1)
	@echo ""
	@echo "Pre-flight checks passed"

deploy-preview-gke:
	@echo "Deploying to Preview GKE"
	@$(MAKE) preflight-preview-gke
	@echo ""
	@echo "Applying Kustomize manifests..."
	kubectl apply -k deployments/overlays/preview-gke
	@echo ""
	@echo "Waiting for rollouts..."
	@kubectl rollout status deployment/preview-mcp-server-langgraph -n preview-mcp-server-langgraph --timeout=10m || true
	@kubectl rollout status deployment/preview-keycloak -n preview-mcp-server-langgraph --timeout=10m || true
	@kubectl rollout status deployment/preview-openfga -n preview-mcp-server-langgraph --timeout=10m || true
	@echo ""
	@echo "Preview GKE deployment complete"
	@echo ""
	@echo "Next: Run 'make postflight-preview-gke' to validate"

postflight-preview-gke:
	@echo "Preview GKE Post-Flight Validation"
	./scripts/gcp/validate-preview-deployment.sh

smoke-test-preview-gke:
	@echo "Preview GKE Smoke Tests"
	./scripts/gcp/preview-smoke-tests.sh

teardown-preview-gke:
	@echo "Preview GKE Teardown (Kubernetes Resources)"
	kubectl delete -k deployments/overlays/preview-gke --ignore-not-found=true || true
	@echo ""
	@echo "Kubernetes resources deleted"
	@echo ""
	@echo "Note: To teardown infrastructure, run:"
	@echo "  ./scripts/gcp/teardown-preview-infrastructure.sh"

teardown-preview-infra:
	@echo "WARNING: Full Preview Infrastructure Teardown"
	@echo "This will DELETE GKE cluster, Cloud SQL, Redis, VPC, etc."
	./scripts/gcp/teardown-preview-infrastructure.sh

deploy-rollback-preview-gke:
	@echo "Rolling back Preview GKE deployment..."
	kubectl rollout undo deployment/preview-mcp-server-langgraph -n preview-mcp-server-langgraph
	kubectl rollout status deployment/preview-mcp-server-langgraph -n preview-mcp-server-langgraph
	@echo "Preview GKE rollback complete"

# Single-command GKE Preview
gke-preview-up:
	@echo "GKE Preview Environment - Full Setup"
	@echo ""
	@echo "This will create:"
	@echo "  - GKE Autopilot cluster (~15 min)"
	@echo "  - Cloud SQL PostgreSQL HA (~10 min)"
	@echo "  - Memorystore Redis HA (~5 min)"
	@echo "  - VPC, Cloud NAT, networking"
	@echo "  - Kubernetes workloads"
	@echo ""
	@echo "Estimated time: 25-30 minutes"
	@echo "Estimated cost: ~$$325/month"
	@echo ""
	./scripts/gcp/gke-preview-up.sh

gke-preview-down:
	@echo "GKE Preview Environment - Full Teardown"
	./scripts/gcp/gke-preview-down.sh

gke-preview-status:
	@echo "GKE Preview Environment Status"
	@echo ""
	@echo "GCP Project: $${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
	@echo "Region: $${GCP_REGION:-us-central1}"
	@echo ""
	@echo "GKE Cluster:"
	@gcloud container clusters describe preview-mcp-server-langgraph-gke \
		--region=$${GCP_REGION:-us-central1} \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(status)" 2>/dev/null && echo "  Status: RUNNING" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "Cloud SQL:"
	@gcloud sql instances describe preview-mcp-slg-postgres \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(state)" 2>/dev/null && echo "  Status: RUNNABLE" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "Memorystore Redis:"
	@gcloud redis instances describe preview-mcp-slg-redis \
		--region=$${GCP_REGION:-us-central1} \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(state)" 2>/dev/null && echo "  Status: READY" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "Kubernetes Pods:"
	@kubectl get pods -n preview-mcp-server-langgraph --no-headers 2>/dev/null | wc -l | xargs -I{} echo "  Count: {} pods" || echo "  Status: No kubectl access"

# Kong targets
setup-kong:
	@echo "Setting up Kong API Gateway..."
	helm repo add kong https://charts.konghq.com
	helm repo update
	helm install kong kong/kong \
		--namespace kong \
		--create-namespace \
		--set ingressController.enabled=true \
		--set proxy.type=LoadBalancer
	@echo "Kong installed"
	@echo ""
	@echo "Apply Kong configurations:"
	@echo "  kubectl apply -k deployments/kubernetes/kong/"

test-rate-limit:
	@echo "Testing rate limits..."
	@for i in $$(seq 1 100); do \
		curl -s -o /dev/null -w "Request $$i: %{http_code}\n" \
			-H "apikey: test-key" \
			http://localhost:8000/; \
		sleep 0.1; \
	done
