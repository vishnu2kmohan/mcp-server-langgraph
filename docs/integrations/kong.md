# Kong API Gateway Integration Guide

Complete guide for integrating MCP Server with LangGraph with Kong API Gateway for rate limiting, authentication, and API management.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Rate Limiting](#rate-limiting)
- [Authentication](#authentication)
- [Deployment](#deployment)
- [Multi-Tenancy](#multi-tenancy)
- [Monitoring](#monitoring)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

## Overview

Kong API Gateway provides:
- **Rate Limiting**: Per-consumer, per-service, global limits
- **Authentication**: JWT, API Key, OAuth2, Basic Auth
- **Traffic Control**: Request/response transformation, routing
- **Security**: IP restriction, bot detection, CORS
- **Observability**: Prometheus metrics, logging, tracing

## Installation

### Option 1: Kong for Kubernetes (Recommended)

```bash
# Add Kong Helm repository
helm repo add kong https://charts.konghq.com
helm repo update

# Install Kong with Kong Ingress Controller
helm install kong kong/kong \
  --namespace kong \
  --create-namespace \
  --set ingressController.enabled=true \
  --set ingressController.installCRDs=false \
  --set proxy.type=LoadBalancer \
  --set admin.enabled=true \
  --set admin.http.enabled=true

# Install Kong CRDs
kubectl apply -f https://raw.githubusercontent.com/Kong/kubernetes-ingress-controller/main/config/crd/bases/configuration.konghq.com_kongplugins.yaml
kubectl apply -f https://raw.githubusercontent.com/Kong/kubernetes-ingress-controller/main/config/crd/bases/configuration.konghq.com_kongconsumers.yaml
kubectl apply -f https://raw.githubusercontent.com/Kong/kubernetes-ingress-controller/main/config/crd/bases/configuration.konghq.com_kongingresses.yaml

# Verify installation
kubectl get pods -n kong
kubectl get svc -n kong
```

### Option 2: Kong DB-less (Declarative Configuration)

```bash
# Install Kong in DB-less mode
helm install kong kong/kong \
  --namespace kong \
  --create-namespace \
  --set env.database=off \
  --set env.declarative_config=/kong/declarative/kong.yaml \
  --set ingressController.enabled=true

# Apply declarative config
kubectl create configmap kong-config \
  --from-file=kong.yaml=kong/kong.yaml \
  -n kong
```

## Rate Limiting

### Basic Rate Limiting (All Users)

```yaml
# Apply to all traffic
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-basic
  namespace: langgraph-agent
spec:
  plugin: rate-limiting
  config:
    minute: 60      # 60 requests per minute
    hour: 1000      # 1000 requests per hour
    policy: local   # local or redis for distributed
```

**Apply to Ingress:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: langgraph-agent
  annotations:
    konghq.com/plugins: rate-limit-basic
spec:
  # ... ingress configuration
```

### Redis-based Rate Limiting (Distributed)

For multi-replica Kong deployments, use Redis for shared state:

```bash
# Deploy Redis
kubectl apply -f kubernetes/kong/redis-deployment.yaml
```

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-distributed
spec:
  plugin: rate-limiting
  config:
    minute: 100
    hour: 5000
    policy: redis
    redis_host: redis
    redis_port: 6379
    redis_database: 0
    fault_tolerant: true  # Continue if Redis unavailable
```

### Tiered Rate Limiting

**Free Tier (60 req/min, 1,000 req/hour):**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-free
spec:
  plugin: rate-limiting
  config:
    minute: 60
    hour: 1000
```

**Premium Tier (300 req/min, 10,000 req/hour):**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-premium
spec:
  plugin: rate-limiting
  config:
    minute: 300
    hour: 10000
```

**Enterprise Tier (1,000 req/min, 100,000 req/hour):**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-enterprise
spec:
  plugin: rate-limiting
  config:
    minute: 1000
    hour: 100000
```

### Advanced Rate Limiting

**Per-consumer with consumer groups:**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-advanced
spec:
  plugin: rate-limiting-advanced
  config:
    limit:
      - 100
    window_size:
      - 60
    namespace: langgraph-agent
    strategy: redis
    enforce_consumer_groups: true
    consumer_groups_limits:
      free_tier:
        - 10
      premium_tier:
        - 100
      enterprise_tier:
        - 1000
```

## Authentication

### API Key Authentication

**1. Create KongPlugin:**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: api-key-auth
spec:
  plugin: key-auth
  config:
    key_names:
      - apikey
      - x-api-key
    hide_credentials: true
```

**2. Create Consumer:**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongConsumer
metadata:
  name: user-alice
username: alice
---
apiVersion: configuration.konghq.com/v1
kind: KongCredential
metadata:
  name: alice-apikey
consumerRef: user-alice
type: key-auth
config:
  key: alice-secret-api-key-12345
```

**3. Test:**
```bash
curl -H "apikey: alice-secret-api-key-12345" \
  https://langgraph-agent.example.com/
```

### JWT Authentication

**1. Create KongPlugin:**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-auth
spec:
  plugin: jwt
  config:
    claims_to_verify:
      - exp
    key_claim_name: iss
    maximum_expiration: 86400
```

**2. Create Consumer with JWT:**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongConsumer
metadata:
  name: user-bob
username: bob
---
apiVersion: configuration.konghq.com/v1
kind: KongCredential
metadata:
  name: bob-jwt
consumerRef: user-bob
type: jwt
config:
  key: bob-issuer
  algorithm: HS256
  secret: bob-jwt-secret-change-me
```

**3. Generate and test JWT:**
```python
import jwt
import datetime

payload = {
    'iss': 'bob-issuer',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
}

token = jwt.encode(payload, 'bob-jwt-secret-change-me', algorithm='HS256')
print(f"JWT: {token}")
```

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://langgraph-agent.example.com/
```

### OAuth2 Authentication

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: oauth2
spec:
  plugin: oauth2
  config:
    scopes:
      - read
      - write
    mandatory_scope: true
    enable_authorization_code: true
    enable_implicit_grant: true
    enable_client_credentials: true
```

## Deployment

### Deploy with Kubernetes Manifests

```bash
# Deploy Redis for distributed rate limiting
kubectl apply -f kubernetes/kong/redis-deployment.yaml

# Deploy Kong plugins
kubectl apply -f kubernetes/kong/kong-plugins.yaml

# Deploy Kong consumers
kubectl apply -f kubernetes/kong/kong-consumers.yaml

# Deploy Kong ingress
kubectl apply -f kubernetes/kong/kong-ingress.yaml

# Or deploy all at once with Kustomize
kubectl apply -k kubernetes/kong/
```

### Deploy with Helm

```bash
# Install agent with Kong enabled
helm install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set kong.enabled=true \
  --set kong.rateLimitTier=premium \
  --set kong.hosts[0]=langgraph-agent.example.com
```

**Custom values file:**
```yaml
# values-kong.yaml
kong:
  enabled: true
  hosts:
    - api.langgraph.example.com
  rateLimitTier: premium
  plugins:
    - rate-limit-premium
    - jwt-auth
    - request-size-limit
    - cors
    - prometheus
  tls:
    enabled: true
    secretName: langgraph-tls
```

```bash
helm install langgraph-agent ./helm/langgraph-agent \
  -f values-kong.yaml
```

## Multi-Tenancy

### Separate Endpoints per Tier

**Free Tier:**
```
https://free.langgraph-agent.example.com
Rate limit: 60 req/min
```

**Premium Tier:**
```
https://premium.langgraph-agent.example.com
Rate limit: 300 req/min
```

**Enterprise Tier:**
```
https://enterprise.langgraph-agent.example.com
Rate limit: 1,000 req/min
```

### Path-based Routing

```yaml
# Free tier: /api/v1/free/*
# Premium tier: /api/v1/premium/*
# Enterprise tier: /api/v1/enterprise/*

services:
  - name: langgraph-agent
    routes:
      - name: free-tier
        paths: [/api/v1/free]
        plugins:
          - name: rate-limiting
            config:
              minute: 60

      - name: premium-tier
        paths: [/api/v1/premium]
        plugins:
          - name: rate-limiting
            config:
              minute: 300

      - name: enterprise-tier
        paths: [/api/v1/enterprise]
        plugins:
          - name: rate-limiting
            config:
              minute: 1000
```

### Consumer Groups

```yaml
apiVersion: configuration.konghq.com/v1beta1
kind: KongConsumerGroup
metadata:
  name: premium-users
spec:
  name: premium_tier
---
# Assign consumer to group
apiVersion: configuration.konghq.com/v1
kind: KongConsumer
metadata:
  name: alice
  annotations:
    konghq.com/consumer-groups: premium_tier
```

## Monitoring

### Prometheus Metrics

**Enable Prometheus plugin:**
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: prometheus
spec:
  plugin: prometheus
  config:
    per_consumer: true
    status_code_metrics: true
    latency_metrics: true
    bandwidth_metrics: true
```

**Metrics exposed at:**
```
http://<kong-proxy>:8001/metrics
```

**Example metrics:**
```
kong_http_requests_total{service="langgraph-agent",route="public",code="200"}
kong_latency_ms{service="langgraph-agent",type="request"}
kong_bandwidth_bytes{service="langgraph-agent",type="ingress"}
```

### ServiceMonitor for Prometheus Operator

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kong-metrics
  namespace: kong
spec:
  selector:
    matchLabels:
      app: kong
  endpoints:
  - port: admin
    path: /metrics
    interval: 30s
```

### Request Logging

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: http-log
spec:
  plugin: http-log
  config:
    http_endpoint: http://logstash:8080/kong
    method: POST
    timeout: 10000
    flush_timeout: 2
    retry_count: 10
```

## Advanced Features

### Request/Response Transformation

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: request-transformer
spec:
  plugin: request-transformer
  config:
    add:
      headers:
        - X-Kong-Request-Id:$(uuid)
        - X-Forwarded-Proto:https
    remove:
      headers:
        - X-Internal-Header
    replace:
      headers:
        - User-Agent:Kong/3.0
```

### IP Restriction

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: ip-restriction
spec:
  plugin: ip-restriction
  config:
    allow:
      - 10.0.0.0/8
      - 172.16.0.0/12
    deny:
      - 192.168.1.100
```

### Bot Detection

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: bot-detection
spec:
  plugin: bot-detection
  config:
    allow:
      - googlebot
      - bingbot
    deny:
      - scrapy
      - curl
```

### Circuit Breaker

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: request-termination
spec:
  plugin: request-termination
  config:
    status_code: 503
    message: "Service temporarily unavailable"
```

Enable during maintenance:
```bash
kubectl patch kongplugin request-termination \
  -n langgraph-agent \
  --type='json' \
  -p='[{"op": "replace", "path": "/disabled", "value": false}]'
```

### Canary Releases

```yaml
services:
  - name: langgraph-agent-v1
    url: http://langgraph-agent-v1:80
    routes:
      - name: stable
        paths: [/]
        plugins:
          - name: canary
            config:
              percentage: 90

  - name: langgraph-agent-v2
    url: http://langgraph-agent-v2:80
    routes:
      - name: canary
        paths: [/]
        plugins:
          - name: canary
            config:
              percentage: 10
```

## Troubleshooting

### Check Kong Status

```bash
# Kong pods
kubectl get pods -n kong

# Kong services
kubectl get svc -n kong

# Kong configuration
kubectl get kongplugins,kongconsumers,kongingresses -n langgraph-agent
```

### Test Rate Limiting

```bash
# Send multiple requests
for i in {1..100}; do
  curl -H "apikey: test-key" \
    -w "\nStatus: %{http_code}\n" \
    https://langgraph-agent.example.com/
  sleep 0.1
done

# Expected: 429 Too Many Requests after limit exceeded
```

### Check Rate Limit Headers

```bash
curl -I -H "apikey: test-key" \
  https://langgraph-agent.example.com/

# Response headers:
# X-RateLimit-Limit-Minute: 60
# X-RateLimit-Remaining-Minute: 59
# X-RateLimit-Limit-Hour: 1000
# X-RateLimit-Remaining-Hour: 999
```

### Debug Kong Logs

```bash
# Kong proxy logs
kubectl logs -n kong deployment/kong-kong -f

# Kong ingress controller logs
kubectl logs -n kong deployment/kong-kong-controller -f

# Check plugin errors
kubectl describe kongplugin rate-limit-basic -n langgraph-agent
```

### Common Issues

**Rate limiting not working:**
- Check plugin is applied to route/service
- Verify Redis connectivity (for distributed)
- Check consumer credentials

**Authentication failures:**
- Verify consumer exists
- Check credential format
- Review JWT expiration

**502 Bad Gateway:**
- Check backend service is running
- Verify service name in Kong configuration
- Check health checks

### Kong Admin API

```bash
# Port forward Kong admin
kubectl port-forward -n kong svc/kong-kong-admin 8001:8001

# List services
curl http://localhost:8001/services

# List routes
curl http://localhost:8001/routes

# List plugins
curl http://localhost:8001/plugins

# List consumers
curl http://localhost:8001/consumers

# Get consumer rate limit status
curl http://localhost:8001/consumers/alice/plugins
```

## Testing Rate Limits

### Python Test Script

```python
import requests
import time

url = "https://langgraph-agent.example.com/"
headers = {"apikey": "test-api-key"}

for i in range(100):
    response = requests.get(url, headers=headers)

    print(f"Request {i+1}: {response.status_code}")

    if response.status_code == 429:
        print("Rate limit exceeded!")
        print(f"Retry-After: {response.headers.get('Retry-After')}")
        print(f"X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining-Minute')}")
        break

    time.sleep(0.5)
```

## Production Checklist

- [ ] Use Redis for distributed rate limiting
- [ ] Configure appropriate rate limits per tier
- [ ] Enable authentication (JWT or API Key)
- [ ] Set up monitoring and alerting
- [ ] Configure health checks
- [ ] Enable request logging
- [ ] Set up IP whitelisting if needed
- [ ] Configure bot detection
- [ ] Test rate limiting before production
- [ ] Document rate limits in API docs
- [ ] Set up consumer management
- [ ] Configure CORS appropriately
- [ ] Enable Prometheus metrics
- [ ] Test failover scenarios

## Resources

- [Kong Documentation](https://docs.konghq.com/)
- [Kong for Kubernetes](https://docs.konghq.com/kubernetes-ingress-controller/)
- [Rate Limiting Plugin](https://docs.konghq.com/hub/kong-inc/rate-limiting/)
- [Kong Plugins Hub](https://docs.konghq.com/hub/)
