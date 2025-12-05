# GCP Preview Environment Configuration
# Auto-generated for CI/CD remediation

project_id     = "vishnu-sandbox-20250310"
project_number = "1024691643349"
region         = "us-central1"
team           = "platform"

app_namespace = "preview-mcp-server-langgraph"

# Monitoring (no channels configured yet)
monitoring_notification_channels = []

# Security (disabled for preview to allow easy access)
enable_cloud_armor                = false
enable_binary_authorization       = false
enable_fleet_registration         = false
enable_master_authorized_networks = false
master_authorized_networks_cidrs  = []

# Deletion protection (disabled for preview to allow teardown)
enable_deletion_protection = false

# Databases
additional_databases = []

# Secret Manager secrets (none configured yet)
app_secret_ids = []
