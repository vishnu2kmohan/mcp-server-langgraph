#!/bin/bash
# One-time setup script for AWS EKS staging infrastructure
# This script provisions all required AWS resources for the staging environment

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="aws-staging"
PROJECT_NAME="mcp-langgraph"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found"
        exit 1
    fi

    if ! command -v terraform &> /dev/null; then
        log_error "Terraform not found"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found"
        exit 1
    fi

    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    log_info "✓ Prerequisites met"
}

setup_terraform_backend() {
    log_info "Setting up Terraform S3 backend..."

    BUCKET_NAME="${PROJECT_NAME}-terraform-state-${AWS_REGION}-${AWS_ACCOUNT_ID}"
    TABLE_NAME="${PROJECT_NAME}-terraform-locks"

    # Create S3 bucket
    if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled
        aws s3api put-bucket-encryption \
            --bucket "$BUCKET_NAME" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
        log_info "✓ Created S3 bucket: $BUCKET_NAME"
    else
        log_info "✓ S3 bucket already exists: $BUCKET_NAME"
    fi

    # Create DynamoDB table
    if ! aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &>/dev/null; then
        aws dynamodb create-table \
            --table-name "$TABLE_NAME" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION"
        log_info "✓ Created DynamoDB table: $TABLE_NAME"
    else
        log_info "✓ DynamoDB table already exists: $TABLE_NAME"
    fi
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."

    cd "terraform/environments/$ENVIRONMENT"

    # Initialize Terraform
    terraform init \
        -backend-config="bucket=${PROJECT_NAME}-terraform-state-${AWS_REGION}-${AWS_ACCOUNT_ID}" \
        -backend-config="key=environments/${ENVIRONMENT}/terraform.tfstate" \
        -backend-config="region=${AWS_REGION}" \
        -backend-config="dynamodb_table=${PROJECT_NAME}-terraform-locks" \
        -backend-config="encrypt=true"

    # Plan
    terraform plan -out=tfplan

    # Apply
    log_warn "About to create AWS resources. This will incur costs (~$324/month for staging)."
    read -p "Continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log_error "Deployment cancelled"
        exit 1
    fi

    terraform apply tfplan

    cd ../../..

    log_info "✓ Infrastructure deployed"
}

configure_kubectl() {
    log_info "Configuring kubectl..."

    CLUSTER_NAME=$(terraform -chdir="terraform/environments/$ENVIRONMENT" output -raw cluster_name)

    aws eks update-kubeconfig \
        --region "$AWS_REGION" \
        --name "$CLUSTER_NAME"

    log_info "✓ kubectl configured for cluster: $CLUSTER_NAME"
}

deploy_monitoring() {
    log_info "Setting up CloudWatch monitoring..."

    CLUSTER_NAME=$(terraform -chdir="terraform/environments/$ENVIRONMENT" output -raw cluster_name)

    export EKS_CLUSTER_NAME="$CLUSTER_NAME"
    export AWS_REGION="$AWS_REGION"

    cd monitoring/aws
    ./setup-monitoring.sh
    cd ../..

    log_info "✓ Monitoring configured"
}

print_summary() {
    log_info "\n=========================================="
    log_info "STAGING INFRASTRUCTURE SETUP COMPLETE!"
    log_info "==========================================\n"

    CLUSTER_NAME=$(terraform -chdir="terraform/environments/$ENVIRONMENT" output -raw cluster_name)
    RDS_ENDPOINT=$(terraform -chdir="terraform/environments/$ENVIRONMENT" output -raw rds_endpoint)
    REDIS_ENDPOINT=$(terraform -chdir="terraform/environments/$ENVIRONMENT" output -raw redis_endpoint)

    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $AWS_REGION"
    log_info "EKS Cluster: $CLUSTER_NAME"
    log_info "RDS Endpoint: $RDS_ENDPOINT"
    log_info "Redis Endpoint: $REDIS_ENDPOINT"
    echo ""
    log_info "Next steps:"
    log_info "1. Deploy application:"
    log_info "   export AWS_ENVIRONMENT=aws-staging"
    log_info "   ./scripts/deploy-aws-eks.sh"
    echo ""
    log_info "2. Access CloudWatch Dashboard:"
    log_info "   https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards"
    echo ""
    log_info "3. To teardown (when done):"
    log_info "   cd terraform/environments/$ENVIRONMENT"
    log_info "   terraform destroy"
}

# Main
main() {
    log_info "Starting AWS EKS staging infrastructure setup..."

    check_prerequisites
    setup_terraform_backend
    deploy_infrastructure
    configure_kubectl
    deploy_monitoring
    print_summary

    log_info "\n✓ Setup completed successfully!"
}

main "$@"
