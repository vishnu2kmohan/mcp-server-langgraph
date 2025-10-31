# Makefile for Terraform Testing and Validation
# Implements Test-Driven Development for Infrastructure as Code

.PHONY: help init validate format lint security test clean install-tools

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(CYAN)Terraform Testing & Validation$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2}'

install-tools: ## Install required testing tools
	@echo "$(YELLOW)Installing Terraform testing tools...$(NC)"
	@command -v terraform >/dev/null 2>&1 || { echo "$(RED)Error: terraform not found. Install from https://terraform.io$(NC)"; exit 1; }
	@command -v tflint >/dev/null 2>&1 || { echo "Installing tflint..."; brew install tflint || curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash; }
	@command -v tfsec >/dev/null 2>&1 || { echo "Installing tfsec..."; brew install tfsec || curl -s https://raw.githubusercontent.com/aquasecurity/tfsec/master/scripts/install_linux.sh | bash; }
	@command -v checkov >/dev/null 2>&1 || { echo "Installing checkov..."; pip install checkov; }
	@command -v terraform-docs >/dev/null 2>&1 || { echo "Installing terraform-docs..."; brew install terraform-docs || { curl -sSLo ./terraform-docs.tar.gz https://terraform-docs.io/dl/v0.16.0/terraform-docs-v0.16.0-$(uname)-amd64.tar.gz && tar -xzf terraform-docs.tar.gz && sudo mv terraform-docs /usr/local/bin/ && rm terraform-docs.tar.gz; }; }
	@echo "$(GREEN)✓ All tools installed$(NC)"

init: ## Initialize all Terraform modules
	@echo "$(YELLOW)Initializing Terraform modules...$(NC)"
	@for dir in modules/*; do \
		if [ -d "$$dir" ]; then \
			echo "$(CYAN)Initializing $$dir...$(NC)"; \
			cd $$dir && terraform init -upgrade && cd ../..; \
		fi \
	done
	@echo "$(GREEN)✓ Initialization complete$(NC)"

validate: ## Validate all Terraform configurations
	@echo "$(YELLOW)Validating Terraform configurations...$(NC)"
	@errors=0; \
	for dir in modules/* environments/*; do \
		if [ -d "$$dir" ] && [ -f "$$dir/main.tf" ]; then \
			echo "$(CYAN)Validating $$dir...$(NC)"; \
			cd $$dir && terraform init -backend=false >/dev/null 2>&1 && terraform validate || { echo "$(RED)✗ Validation failed for $$dir$(NC)"; errors=$$((errors+1)); }; \
			cd - >/dev/null; \
		fi \
	done; \
	if [ $$errors -eq 0 ]; then \
		echo "$(GREEN)✓ All configurations are valid$(NC)"; \
	else \
		echo "$(RED)✗ $$errors module(s) failed validation$(NC)"; \
		exit 1; \
	fi

format: ## Format all Terraform files
	@echo "$(YELLOW)Formatting Terraform files...$(NC)"
	@terraform fmt -recursive .
	@echo "$(GREEN)✓ Formatting complete$(NC)"

format-check: ## Check if files are formatted correctly
	@echo "$(YELLOW)Checking Terraform formatting...$(NC)"
	@terraform fmt -check -recursive . || { echo "$(RED)✗ Files need formatting. Run 'make format'$(NC)"; exit 1; }
	@echo "$(GREEN)✓ All files are properly formatted$(NC)"

lint: ## Run TFLint on all modules
	@echo "$(YELLOW)Running TFLint...$(NC)"
	@tflint --init
	@errors=0; \
	for dir in modules/* environments/*; do \
		if [ -d "$$dir" ] && [ -f "$$dir/main.tf" ]; then \
			echo "$(CYAN)Linting $$dir...$(NC)"; \
			cd $$dir && tflint || { echo "$(RED)✗ Linting failed for $$dir$(NC)"; errors=$$((errors+1)); }; \
			cd - >/dev/null; \
		fi \
	done; \
	if [ $$errors -eq 0 ]; then \
		echo "$(GREEN)✓ Linting passed$(NC)"; \
	else \
		echo "$(RED)✗ $$errors module(s) failed linting$(NC)"; \
		exit 1; \
	fi

security: ## Run security scans (tfsec and checkov)
	@echo "$(YELLOW)Running security scans...$(NC)"
	@echo "$(CYAN)Running tfsec...$(NC)"
	@tfsec . --minimum-severity MEDIUM || { echo "$(RED)✗ tfsec found security issues$(NC)"; exit 1; }
	@echo "$(CYAN)Running checkov...$(NC)"
	@checkov -d . --quiet --compact --framework terraform || { echo "$(RED)✗ checkov found security issues$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Security scans passed$(NC)"

security-report: ## Generate detailed security report
	@echo "$(YELLOW)Generating security report...$(NC)"
	@mkdir -p reports
	@echo "Running tfsec..."
	@tfsec . --format json > reports/tfsec-report.json || true
	@tfsec . --format sarif > reports/tfsec-report.sarif || true
	@echo "Running checkov..."
	@checkov -d . --output json > reports/checkov-report.json || true
	@checkov -d . --output cli > reports/checkov-report.txt || true
	@echo "$(GREEN)✓ Reports generated in ./reports/$(NC)"

docs: ## Generate documentation for all modules
	@echo "$(YELLOW)Generating module documentation...$(NC)"
	@for dir in modules/*; do \
		if [ -d "$$dir" ] && [ -f "$$dir/main.tf" ]; then \
			echo "$(CYAN)Documenting $$dir...$(NC)"; \
			terraform-docs markdown table $$dir > $$dir/README.md; \
		fi \
	done
	@echo "$(GREEN)✓ Documentation generated$(NC)"

test-vpc: ## Test VPC module
	@echo "$(YELLOW)Testing VPC module...$(NC)"
	@cd modules/vpc && terraform init -backend=false && terraform validate
	@echo "$(GREEN)✓ VPC module tests passed$(NC)"

test-eks: ## Test EKS module
	@echo "$(YELLOW)Testing EKS module...$(NC)"
	@cd modules/eks && terraform init -backend=false && terraform validate
	@echo "$(GREEN)✓ EKS module tests passed$(NC)"

test-rds: ## Test RDS module
	@echo "$(YELLOW)Testing RDS module...$(NC)"
	@cd modules/rds && terraform init -backend=false && terraform validate
	@echo "$(GREEN)✓ RDS module tests passed$(NC)"

test-elasticache: ## Test ElastiCache module
	@echo "$(YELLOW)Testing ElastiCache module...$(NC)"
	@cd modules/elasticache && terraform init -backend=false && terraform validate
	@echo "$(GREEN)✓ ElastiCache module tests passed$(NC)"

test-iam: ## Test IAM module
	@echo "$(YELLOW)Testing IAM module...$(NC)"
	@cd modules/iam && terraform init -backend=false && terraform validate
	@echo "$(GREEN)✓ IAM module tests passed$(NC)"

test: validate format-check lint security ## Run all tests
	@echo "$(GREEN)✓ All tests passed$(NC)"

cost-estimate: ## Estimate infrastructure costs using infracost
	@echo "$(YELLOW)Estimating infrastructure costs...$(NC)"
	@command -v infracost >/dev/null 2>&1 || { echo "$(RED)Error: infracost not found. Install from https://www.infracost.io/docs/$(NC)"; exit 1; }
	@for env in dev staging prod; do \
		if [ -d "environments/$$env" ]; then \
			echo "$(CYAN)Cost estimate for $$env:$(NC)"; \
			cd environments/$$env && infracost breakdown --path . && cd ../..; \
		fi \
	done

plan-dev: ## Plan dev environment
	@echo "$(YELLOW)Planning dev environment...$(NC)"
	@cd environments/dev && terraform plan

plan-staging: ## Plan staging environment
	@echo "$(YELLOW)Planning staging environment...$(NC)"
	@cd environments/staging && terraform plan

plan-prod: ## Plan production environment
	@echo "$(YELLOW)Planning production environment...$(NC)"
	@cd environments/prod && terraform plan

clean: ## Clean Terraform artifacts
	@echo "$(YELLOW)Cleaning Terraform artifacts...$(NC)"
	@find . -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".terraform.lock.hcl" -delete 2>/dev/null || true
	@find . -type f -name "terraform.tfstate*" -delete 2>/dev/null || true
	@find . -type f -name "*.tfplan" -delete 2>/dev/null || true
	@rm -rf reports/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

pre-commit: format-check validate lint security ## Run all pre-commit checks
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

ci: test docs ## Run CI pipeline checks
	@echo "$(GREEN)✓ CI checks complete$(NC)"

.PHONY: install-tools init validate format format-check lint security security-report
.PHONY: docs test-vpc test-eks test-rds test-elasticache test-iam test
.PHONY: cost-estimate plan-dev plan-staging plan-prod clean pre-commit ci
