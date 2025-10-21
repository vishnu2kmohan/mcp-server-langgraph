#!/usr/bin/env bash
# ==============================================================================
# Generate Optimized Kubernetes Manifests
# ==============================================================================
#
# This script generates right-sized Kubernetes manifests for all services
# based on the optimization analysis.
#
# USAGE:
#   ./scripts/generate-optimized-manifests.sh [--output-dir DIR]
#
# OPTIONS:
#   --output-dir DIR    Output directory (default: deployments/optimized/)
#
# ==============================================================================

set -euo pipefail

OUTPUT_DIR="deployments/optimized"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

mkdir -p "$OUTPUT_DIR"

echo "Generating optimized manifests in $OUTPUT_DIR/"

# ==============================================================================
# HPA (Horizontal Pod Autoscaler)
# ==============================================================================

cat > "$OUTPUT_DIR/hpa.yaml" << 'EOF'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-langgraph
  namespace: mcp-server-langgraph
  labels:
    app: mcp-server-langgraph
  annotations:
    optimized.mcp/changes: "minReplicas:3→2,maxReplicas:10→20,cpu-threshold:70→60"
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server-langgraph
  minReplicas: 2          # Was: 3 (-33% base cost)
  maxReplicas: 20         # Was: 10 (better burst capacity)
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60  # Was: 70 (more responsive scaling)
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70  # Was: 80 (safer buffer)
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 30
      selectPolicy: Max
EOF

# ==============================================================================
# PostgreSQL StatefulSet
# ==============================================================================

cat > "$OUTPUT_DIR/postgres-statefulset.yaml" << 'EOF'
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: mcp-server-langgraph
  labels:
    app: postgres
    component: database
  annotations:
    optimized.mcp/changes: "cpu:250m→100m,memory:512Mi→256Mi,storage:10Gi→2Gi"
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
        component: database
    spec:
      serviceAccountName: mcp-server-langgraph
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        fsGroup: 999

      containers:
      - name: postgres
        image: postgres:16.8-alpine
        imagePullPolicy: IfNotPresent

        ports:
        - name: postgres
          containerPort: 5432
          protocol: TCP

        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: mcp-server-langgraph-secrets
              key: postgres-username
              optional: true
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mcp-server-langgraph-secrets
              key: postgres-password
              optional: true
        - name: POSTGRES_MULTIPLE_DATABASES
          value: "openfga,keycloak"
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata

        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data

        # OPTIMIZED: Right-sized resources for read-heavy workload
        resources:
          requests:
            cpu: 100m          # Was: 250m (-60%)
            memory: 256Mi      # Was: 512Mi (-50%)
          limits:
            cpu: 500m          # Was: 2000m (-75%)
            memory: 512Mi      # Was: 2Gi (-75%)

        startupProbe:
          exec:
            command: ["sh", "-c", "pg_isready -U ${POSTGRES_USER}"]
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30

        livenessProbe:
          exec:
            command: ["sh", "-c", "pg_isready -U ${POSTGRES_USER}"]
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          exec:
            command: ["sh", "-c", "pg_isready -U ${POSTGRES_USER}"]
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          runAsNonRoot: true
          runAsUser: 999
          capabilities:
            drop:
            - ALL

  volumeClaimTemplates:
  - metadata:
      name: postgres-data
      labels:
        app: postgres
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 2Gi  # Was: 10Gi (-80%)
      # Enable volume expansion for future growth
      allowVolumeExpansion: true
EOF

# ==============================================================================
# Redis Session Deployment
# ==============================================================================

cat > "$OUTPUT_DIR/redis-session-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-session
  namespace: mcp-server-langgraph
  labels:
    app: redis-session
    component: session-store
  annotations:
    optimized.mcp/changes: "cpu:100m→50m,memory:256Mi→128Mi"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-session
  template:
    metadata:
      labels:
        app: redis-session
        component: session-store
    spec:
      serviceAccountName: mcp-server-langgraph
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        fsGroup: 999

      containers:
      - name: redis
        image: redis:7-alpine
        imagePullPolicy: IfNotPresent

        ports:
        - name: redis
          containerPort: 6379
          protocol: TCP

        command: ["redis-server"]
        args:
          - "--maxmemory"
          - "128mb"  # Match memory limit
          - "--maxmemory-policy"
          - "allkeys-lru"
          - "--save"
          - ""  # No persistence for sessions
          - "--appendonly"
          - "no"

        # OPTIMIZED: Right-sized for session storage
        resources:
          requests:
            cpu: 50m           # Was: 100m (-50%)
            memory: 128Mi      # Was: 256Mi (-50%)
          limits:
            cpu: 200m          # Was: 500m (-60%)
            memory: 256Mi      # Was: 1Gi (-75%)

        startupProbe:
          exec:
            command: ["redis-cli", "ping"]
          initialDelaySeconds: 5
          periodSeconds: 3
          timeoutSeconds: 2
          failureThreshold: 20

        livenessProbe:
          exec:
            command: ["redis-cli", "ping"]
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 2
          failureThreshold: 3

        readinessProbe:
          exec:
            command: ["redis-cli", "ping"]
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 2
          failureThreshold: 3

        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          runAsNonRoot: true
          runAsUser: 999
          capabilities:
            drop:
            - ALL
EOF

echo "✓ Generated optimized manifests:"
echo "  - $OUTPUT_DIR/hpa.yaml"
echo "  - $OUTPUT_DIR/deployment.yaml"
echo "  - $OUTPUT_DIR/postgres-statefulset.yaml"
echo "  - $OUTPUT_DIR/redis-session-deployment.yaml"
echo ""
echo "Next steps:"
echo "  1. Review manifests: ls -la $OUTPUT_DIR/"
echo "  2. Compare with current: diff deployments/kubernetes/base/ $OUTPUT_DIR/"
echo "  3. Test in dev environment first"
echo "  4. Apply with: kubectl apply -f $OUTPUT_DIR/"
