package main

import data.lib.kubernetes

# Deny resources with hardcoded namespaces that don't match overlay namespace
deny[msg] {
    # Get the resource
    input.kind
    input.metadata.namespace

    # Known mismatches from Codex findings
    hardcoded_namespace := input.metadata.namespace

    # Check for common mistakes
    mistakes := {
        "mcp-staging": "staging-mcp-server-langgraph",
        "mcp-production": "production-mcp-server-langgraph"
    }

    expected := mistakes[hardcoded_namespace]

    msg := sprintf(
        "%s '%s' has hardcoded namespace '%s' which should be '%s'. Remove the namespace field and let the overlay set it.",
        [input.kind, input.metadata.name, hardcoded_namespace, expected]
    )
}

# Deny ResourceQuotas for undefined namespaces
deny[msg] {
    input.kind == "ResourceQuota"
    namespace := input.metadata.namespace

    # Only deny if namespace is obviously wrong (not standard and not project namespace)
    not namespace_is_standard(namespace)
    not namespace_is_project(namespace)

    msg := sprintf(
        "ResourceQuota '%s' references namespace '%s' which may not be defined. Ensure the namespace exists or is created first.",
        [input.metadata.name, namespace]
    )
}

# Helper: Check if namespace is a standard Kubernetes namespace
namespace_is_standard(ns) {
    standard_namespaces := {"default", "kube-system", "kube-public", "kube-node-lease"}
    standard_namespaces[ns]
}

# Helper: Check if namespace is a project namespace
namespace_is_project(ns) {
    # Allow project namespaces (mcp-server-langgraph and its variants)
    startswith(ns, "mcp-server-langgraph")
}

namespace_is_project(ns) {
    # Allow overlay-specific namespaces
    project_namespaces := {"staging-mcp-server-langgraph", "production-mcp-server-langgraph", "dev-mcp-server-langgraph"}
    project_namespaces[ns]
}

# Warn about resources without namespace in multi-tenant deployments
warn[msg] {
    input.kind != "Namespace"
    input.kind != "ClusterRole"
    input.kind != "ClusterRoleBinding"
    not input.metadata.namespace

    msg := sprintf(
        "%s '%s' does not specify a namespace. Ensure the overlay sets the namespace correctly.",
        [input.kind, input.metadata.name]
    )
}
