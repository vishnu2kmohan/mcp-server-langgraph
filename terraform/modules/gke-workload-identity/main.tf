# GKE Workload Identity Module
# Creates IAM bindings for Kubernetes service accounts to use GCP service accounts

locals {
  # Workload Identity pool format
  workload_identity_pool = "${var.project_id}.svc.id.goog"
}

#######################
# GCP Service Accounts
#######################

resource "google_service_account" "workload_identity" {
  for_each = var.service_accounts

  project      = var.project_id
  account_id   = each.value.gcp_sa_name
  display_name = each.value.display_name != null ? each.value.display_name : "Workload Identity SA for ${each.key}"
  description  = each.value.description != null ? each.value.description : "Service account for Kubernetes workload ${each.key} in namespace ${var.namespace}"
}

#######################
# IAM Policy Bindings (GCP Service Account -> Kubernetes Service Account)
#######################

resource "google_service_account_iam_member" "workload_identity" {
  for_each = var.service_accounts

  service_account_id = google_service_account.workload_identity[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${local.workload_identity_pool}[${var.namespace}/${each.key}]"
}

#######################
# IAM Role Bindings (GCP Service Account -> GCP Resources)
#######################

resource "google_project_iam_member" "workload_identity_roles" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for role in sa_config.roles : {
          key     = "${sa_name}-${role}"
          sa_name = sa_name
          role    = role
        }
      ]
    ]) : binding.key => binding
  }

  project = var.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.workload_identity[each.value.sa_name].email}"
}

#######################
# Custom IAM Role Bindings (for specific resources)
#######################

# Cloud SQL instance IAM bindings
resource "google_project_iam_member" "cloudsql_client" {
  for_each = {
    for sa_name, sa_config in var.service_accounts :
    sa_name => sa_config
    if lookup(sa_config, "cloudsql_access", false)
  }

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.workload_identity[each.key].email}"
}

# Secret Manager access
resource "google_secret_manager_secret_iam_member" "secrets" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for secret_id in lookup(sa_config, "secret_ids", []) : {
          key       = "${sa_name}-${secret_id}"
          sa_name   = sa_name
          secret_id = secret_id
        }
      ]
    ]) : binding.key => binding
  }

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.workload_identity[each.value.sa_name].email}"
}

# Storage bucket IAM bindings
resource "google_storage_bucket_iam_member" "buckets" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for bucket_config in lookup(sa_config, "bucket_access", []) : {
          key        = "${sa_name}-${bucket_config.bucket_name}"
          sa_name    = sa_name
          bucket     = bucket_config.bucket_name
          role       = bucket_config.role
        }
      ]
    ]) : binding.key => binding
  }

  bucket = each.value.bucket
  role   = each.value.role
  member = "serviceAccount:${google_service_account.workload_identity[each.value.sa_name].email}"
}

# BigQuery dataset IAM bindings
resource "google_bigquery_dataset_iam_member" "datasets" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for dataset_config in lookup(sa_config, "bigquery_access", []) : {
          key        = "${sa_name}-${dataset_config.dataset_id}"
          sa_name    = sa_name
          dataset_id = dataset_config.dataset_id
          role       = dataset_config.role
        }
      ]
    ]) : binding.key => binding
  }

  project    = var.project_id
  dataset_id = each.value.dataset_id
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.workload_identity[each.value.sa_name].email}"
}

# Pub/Sub topic IAM bindings
resource "google_pubsub_topic_iam_member" "topics" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for topic_config in lookup(sa_config, "pubsub_topics", []) : {
          key     = "${sa_name}-${topic_config.topic}"
          sa_name = sa_name
          topic   = topic_config.topic
          role    = topic_config.role
        }
      ]
    ]) : binding.key => binding
  }

  project = var.project_id
  topic   = each.value.topic
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.workload_identity[each.value.sa_name].email}"
}

# Pub/Sub subscription IAM bindings
resource "google_pubsub_subscription_iam_member" "subscriptions" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for sub_config in lookup(sa_config, "pubsub_subscriptions", []) : {
          key          = "${sa_name}-${sub_config.subscription}"
          sa_name      = sa_name
          subscription = sub_config.subscription
          role         = sub_config.role
        }
      ]
    ]) : binding.key => binding
  }

  project      = var.project_id
  subscription = each.value.subscription
  role         = each.value.role
  member       = "serviceAccount:${google_service_account.workload_identity[each.value.sa_name].email}"
}

#######################
# Service Account Keys (for non-Workload Identity use)
#######################

resource "google_service_account_key" "keys" {
  for_each = {
    for sa_name, sa_config in var.service_accounts :
    sa_name => sa_config
    if lookup(sa_config, "create_key", false)
  }

  service_account_id = google_service_account.workload_identity[each.key].name
}
