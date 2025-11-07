package main

# Cloud SQL Proxy health check validation
deny[msg] {
    input.kind in ["Deployment", "StatefulSet"]

    container := input.spec.template.spec.containers[_]
    contains(container.image, "cloud-sql-proxy")

    # Has HTTP probe configured
    has_http_probe(container)

    # But missing required health check flags
    not has_health_check_flag(container.args)

    msg := sprintf(
        "%s '%s' container '%s' has HTTP health probes but missing --health-check flag in args.",
        [input.kind, input.metadata.name, container.name]
    )
}

deny[msg] {
    input.kind in ["Deployment", "StatefulSet"]

    container := input.spec.template.spec.containers[_]
    contains(container.image, "cloud-sql-proxy")

    # Has HTTP probe on specific port
    probe_port := get_http_probe_port(container)
    probe_port != 0

    # But missing --http-port flag
    not has_http_port_flag(container.args)

    msg := sprintf(
        "%s '%s' container '%s' has HTTP probe on port %d but missing --http-port flag.",
        [input.kind, input.metadata.name, container.name, probe_port]
    )
}

warn[msg] {
    input.kind in ["Deployment", "StatefulSet"]

    container := input.spec.template.spec.containers[_]
    contains(container.image, "cloud-sql-proxy")

    has_http_probe(container)
    has_health_check_flag(container.args)
    has_http_port_flag(container.args)

    # But missing --http-address flag
    not has_http_address_flag(container.args)

    msg := sprintf(
        "%s '%s' container '%s' should specify --http-address=0.0.0.0 for health checks to work correctly.",
        [input.kind, input.metadata.name, container.name]
    )
}

# Helper: Check if container has HTTP probe
has_http_probe(container) {
    container.livenessProbe.httpGet
}

has_http_probe(container) {
    container.readinessProbe.httpGet
}

# Helper: Get HTTP probe port
get_http_probe_port(container) = port {
    port := container.livenessProbe.httpGet.port
} else = port {
    port := container.readinessProbe.httpGet.port
} else = 0 {
    true
}

# Helper: Check for health check flag
has_health_check_flag(args) {
    arg := args[_]
    arg == "--health-check"
}

# Helper: Check for http-port flag
has_http_port_flag(args) {
    arg := args[_]
    startswith(arg, "--http-port")
}

# Helper: Check for http-address flag
has_http_address_flag(args) {
    arg := args[_]
    startswith(arg, "--http-address")
}

# General probe validation
warn[msg] {
    input.kind in ["Deployment", "StatefulSet"]

    container := input.spec.template.spec.containers[_]

    # Has liveness probe but no readiness probe
    container.livenessProbe
    not container.readinessProbe

    msg := sprintf(
        "%s '%s' container '%s' has livenessProbe but no readinessProbe. Consider adding both.",
        [input.kind, input.metadata.name, container.name]
    )
}

warn[msg] {
    input.kind in ["Deployment", "StatefulSet"]

    container := input.spec.template.spec.containers[_]

    # Has readiness probe but no liveness probe
    container.readinessProbe
    not container.livenessProbe

    msg := sprintf(
        "%s '%s' container '%s' has readinessProbe but no livenessProbe. Consider adding both.",
        [input.kind, input.metadata.name, container.name]
    )
}
