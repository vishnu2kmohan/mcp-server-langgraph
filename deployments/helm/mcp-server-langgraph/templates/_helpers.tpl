{{/*
Expand the name of the chart.
*/}}
{{- define "mcp-server-langgraph.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "mcp-server-langgraph.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mcp-server-langgraph.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mcp-server-langgraph.labels" -}}
helm.sh/chart: {{ include "mcp-server-langgraph.chart" . }}
{{ include "mcp-server-langgraph.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mcp-server-langgraph.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mcp-server-langgraph.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mcp-server-langgraph.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mcp-server-langgraph.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use
*/}}
{{- define "mcp-server-langgraph.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else if .Values.externalSecrets.enabled }}
{{- include "mcp-server-langgraph.fullname" . }}-external
{{- else }}
{{- include "mcp-server-langgraph.fullname" . }}
{{- end }}
{{- end }}

{{/*
ConfigMap data for checksum calculation
This template renders the configmap data to detect configuration changes
*/}}
{{- define "mcp-server-langgraph.configmapData" -}}
environment: {{ .Values.config.environment | quote }}
log_level: {{ .Values.config.logLevel | quote }}
llm_provider: {{ .Values.config.llmProvider | quote }}
model_name: {{ .Values.config.modelName | quote }}
model_temperature: {{ .Values.config.modelTemperature | quote }}
model_max_tokens: {{ .Values.config.modelMaxTokens | quote }}
model_timeout: {{ .Values.config.modelTimeout | quote }}
enable_fallback: {{ .Values.config.enableFallback | quote }}
max_iterations: {{ .Values.config.maxIterations | quote }}
enable_checkpointing: {{ .Values.config.enableCheckpointing | quote }}
enable_tracing: {{ .Values.config.enableTracing | quote }}
enable_metrics: {{ .Values.config.enableMetrics | quote }}
enable_console_export: {{ .Values.config.enableConsoleExport | quote }}
observability_backend: {{ .Values.config.observabilityBackend | quote }}
langsmith_tracing: {{ .Values.config.langsmithTracing | quote }}
auth_provider: {{ .Values.config.authProvider | quote }}
auth_mode: {{ .Values.config.authMode | quote }}
keycloak_server_url: {{ .Values.config.keycloakServerUrl | quote }}
keycloak_realm: {{ .Values.config.keycloakRealm | quote }}
keycloak_client_id: {{ .Values.config.keycloakClientId | quote }}
keycloak_verify_ssl: {{ .Values.config.keycloakVerifySsl | quote }}
keycloak_timeout: {{ .Values.config.keycloakTimeout | quote }}
keycloak_hostname: {{ .Values.config.keycloakHostname | quote }}
session_backend: {{ .Values.config.sessionBackend | quote }}
redis_url: {{ .Values.config.redisUrl | quote }}
redis_ssl: {{ .Values.config.redisSsl | quote }}
session_ttl_seconds: {{ .Values.config.sessionTtlSeconds | quote }}
session_sliding_window: {{ .Values.config.sessionSlidingWindow | quote }}
session_max_concurrent: {{ .Values.config.sessionMaxConcurrent | quote }}
checkpoint_backend: {{ .Values.config.checkpointBackend | quote }}
checkpoint_redis_url: {{ .Values.config.checkpointRedisUrl | quote }}
checkpoint_redis_ttl: {{ .Values.config.checkpointRedisTtl | quote }}
gdpr_storage_backend: {{ .Values.config.gdprStorageBackend | quote }}
gdpr_postgres_url: {{ .Values.config.gdprPostgresUrl | quote }}
{{- end }}

{{/*
Secret data for checksum calculation
This template renders secret data keys to detect secret changes
*/}}
{{- define "mcp-server-langgraph.secretData" -}}
anthropic-api-key: {{ .Values.secrets.anthropicApiKey | default "REPLACE_ME" | quote }}
google-api-key: {{ .Values.secrets.googleApiKey | default "" | quote }}
openai-api-key: {{ .Values.secrets.openaiApiKey | default "" | quote }}
jwt-secret-key: {{ .Values.secrets.jwtSecretKey | default "REPLACE_ME" | quote }}
openfga-store-id: {{ .Values.secrets.openfgaStoreId | default "" | quote }}
openfga-model-id: {{ .Values.secrets.openfgaModelId | default "" | quote }}
keycloak-client-secret: {{ .Values.secrets.keycloakClientSecret | default "" | quote }}
postgres-username: {{ .Values.secrets.postgresUsername | default "postgres" | quote }}
postgres-password: {{ .Values.secrets.postgresPassword | default "" | quote }}
redis-password: {{ .Values.secrets.redisPassword | default "" | quote }}
langsmith-api-key: {{ .Values.secrets.langsmithApiKey | default "" | quote }}
infisical-client-id: {{ .Values.secrets.infisicalClientId | default "" | quote }}
infisical-client-secret: {{ .Values.secrets.infisicalClientSecret | default "" | quote }}
infisical-project-id: {{ .Values.secrets.infisicalProjectId | default "" | quote }}
{{- end }}
