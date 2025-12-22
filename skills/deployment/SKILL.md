---
name: deployment
version: 1.0.0
description: CI/CD automation and deployment workflow management
category: devops
author: Emergence AI
dependencies: []
sandbox_config:
  network: none
  filesystem: readonly
required_secrets: []
optional_secrets:
  - GITHUB_TOKEN
  - AWS_ACCESS_KEY_ID
  - GCP_SERVICE_ACCOUNT
---

# Deployment Skill

Automate CI/CD workflows and deployment processes.

## Capabilities

- **Pipeline Generation**: Create CI/CD pipeline configs
- **Deployment Scripts**: Generate deployment automation
- **Environment Management**: Handle multi-environment deployments
- **Rollback Planning**: Create rollback strategies

## Usage Examples

- "Generate a GitHub Actions workflow for this project"
- "Create a Kubernetes deployment manifest"
- "Set up blue-green deployment strategy"

## Guidelines

1. Follow infrastructure-as-code principles
2. Include health checks and rollback
3. Use secrets management
4. Document all configurations

## Supported Platforms

- GitHub Actions
- GitLab CI
- Kubernetes/Helm
- Docker Compose
- AWS/GCP/Azure
