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

deploy-stg:
	@echo "Deploying to stg environment..."
	kubectl apply -k deployments/overlays/stg
	@echo "Waiting for rollout..."
	kubectl rollout status deployment/stg-langgraph-agent -n langgraph-agent-stg --timeout=5m
	@echo "STG deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent-stg"
	@echo "  kubectl logs -f deployment/stg-langgraph-agent -n langgraph-agent-stg"

deploy-prod:
	@echo "WARNING: Deploying to PRODUCTION environment"
	@echo "Press Ctrl+C within 10 seconds to cancel..."
	@sleep 10
	@echo "Deploying to prod with Helm..."
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

deploy-rollback-stg:
	@echo "Rolling back stg deployment..."
	kubectl rollout undo deployment/stg-langgraph-agent -n langgraph-agent-stg
	kubectl rollout status deployment/stg-langgraph-agent -n langgraph-agent-stg
	@echo "STG rollback complete"

deploy-rollback-prod:
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
# GKE stg Deployment
# ==============================================================================

preflight-stg-gke:
	@echo "STG GKE Pre-Flight Checks"
	@echo ""
	@echo "Validating Kustomize overlay..."
	@kubectl kustomize deployments/overlays/stg-gke > /dev/null && echo "  Kustomize overlay valid" || (echo "  Kustomize overlay invalid" && exit 1)
	@echo ""
	@echo "Checking GKE cluster access..."
	@kubectl cluster-info > /dev/null 2>&1 && echo "  kubectl connected to cluster" || (echo "  kubectl not connected" && exit 1)
	@echo ""
	@echo "Pre-flight checks passed"

deploy-stg-gke:
	@echo "Deploying to STG GKE"
	@$(MAKE) preflight-stg-gke
	@echo ""
	@echo "Applying Kustomize manifests..."
	kubectl apply -k deployments/overlays/stg-gke
	@echo ""
	@echo "Waiting for rollouts..."
	@kubectl rollout status deployment/stg-mcp-server-langgraph -n stg-mcp-server-langgraph --timeout=10m || true
	@kubectl rollout status deployment/stg-keycloak -n stg-mcp-server-langgraph --timeout=10m || true
	@kubectl rollout status deployment/stg-openfga -n stg-mcp-server-langgraph --timeout=10m || true
	@echo ""
	@echo "STG GKE deployment complete"
	@echo ""
	@echo "Next: Run 'make postflight-stg-gke' to validate"

postflight-stg-gke:
	@echo "STG GKE Post-Flight Validation"
	./scripts/gcp/validate-stg-deployment.sh

smoke-test-stg-gke:
	@echo "STG GKE Smoke Tests"
	./scripts/gcp/stg-smoke-tests.sh

teardown-stg-gke:
	@echo "STG GKE Teardown (Kubernetes Resources)"
	kubectl delete -k deployments/overlays/stg-gke --ignore-not-found=true || true
	@echo ""
	@echo "Kubernetes resources deleted"
	@echo ""
	@echo "Note: To teardown infrastructure, run:"
	@echo "  ./scripts/gcp/teardown-stg-infrastructure.sh"

teardown-stg-infra:
	@echo "WARNING: Full STG Infrastructure Teardown"
	@echo "This will DELETE GKE cluster, Cloud SQL, Redis, VPC, etc."
	./scripts/gcp/teardown-stg-infrastructure.sh

deploy-rollback-stg-gke:
	@echo "Rolling back STG GKE deployment..."
	kubectl rollout undo deployment/stg-mcp-server-langgraph -n stg-mcp-server-langgraph
	kubectl rollout status deployment/stg-mcp-server-langgraph -n stg-mcp-server-langgraph
	@echo "STG GKE rollback complete"

# Single-command GKE stg
gke-stg-up:
	@echo "GKE stg Environment - Full Setup"
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
	./scripts/gcp/gke-stg-up.sh

gke-stg-down:
	@echo "GKE stg Environment - Full Teardown"
	./scripts/gcp/gke-stg-down.sh

gke-stg-status:
	@echo "GKE stg Environment Status"
	@echo ""
	@echo "GCP Project: $${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
	@echo "Region: $${GCP_REGION:-us-central1}"
	@echo ""
	@echo "GKE Cluster:"
	@gcloud container clusters describe stg-mcp-server-langgraph-gke \
		--region=$${GCP_REGION:-us-central1} \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(status)" 2>/dev/null && echo "  Status: RUNNING" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "Cloud SQL:"
	@gcloud sql instances describe stg-mcp-slg-postgres \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(state)" 2>/dev/null && echo "  Status: RUNNABLE" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "Memorystore Redis:"
	@gcloud redis instances describe stg-mcp-slg-redis \
		--region=$${GCP_REGION:-us-central1} \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(state)" 2>/dev/null && echo "  Status: READY" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "Kubernetes Pods:"
	@kubectl get pods -n stg-mcp-server-langgraph --no-headers 2>/dev/null | wc -l | xargs -I{} echo "  Count: {} pods" || echo "  Status: No kubectl access"

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
