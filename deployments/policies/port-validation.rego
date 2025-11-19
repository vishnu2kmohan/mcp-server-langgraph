package main

# PostgreSQL port validation
deny[msg] {
    input.kind == "NetworkPolicy"
    egress := input.spec.egress[_]
    port := egress.ports[_].port

    # MySQL port (3306 or 3307) used instead of PostgreSQL (5432)
    port == 3306
    msg := sprintf(
        "NetworkPolicy '%s' uses port 3306 (MySQL). PostgreSQL uses port 5432.",
        [input.metadata.name]
    )
}

deny[msg] {
    input.kind == "NetworkPolicy"
    egress := input.spec.egress[_]
    port := egress.ports[_].port

    # MySQL proxy port used instead of PostgreSQL
    port == 3307
    msg := sprintf(
        "NetworkPolicy '%s' uses port 3307 (MySQL). PostgreSQL uses port 5432.",
        [input.metadata.name]
    )
}

# Service port validation for databases
deny[msg] {
    input.kind == "Service"
    input.metadata.name
    contains(lower(input.metadata.name), "postgres")

    port := input.spec.ports[_]
    port.port != 5432

    msg := sprintf(
        "Service '%s' appears to be for PostgreSQL but uses port %d instead of 5432.",
        [input.metadata.name, port.port]
    )
}

deny[msg] {
    input.kind == "Service"
    input.metadata.name
    contains(lower(input.metadata.name), "redis")

    port := input.spec.ports[_]
    port.port != 6379

    msg := sprintf(
        "Service '%s' appears to be for Redis but uses port %d instead of 6379.",
        [input.metadata.name, port.port]
    )
}

# Deployment/StatefulSet database connection validation
warn[msg] {
    input.kind in ["Deployment", "StatefulSet"]
    container := input.spec.template.spec.containers[_]
    env := container.env[_]

    # Check for database connection strings with wrong ports
    contains(env.value, ":3306")
    msg := sprintf(
        "%s '%s' container '%s' has env var with MySQL port 3306. Verify this is correct.",
        [input.kind, input.metadata.name, container.name]
    )
}

warn[msg] {
    {"Deployment", "StatefulSet"}[input.kind]
    container := input.spec.template.spec.containers[_]
    env := container.env[_]

    contains(env.value, ":3307")
    msg := sprintf(
        "%s '%s' container '%s' has env var with port 3307. For PostgreSQL, use 5432.",
        [input.kind, input.metadata.name, container.name]
    )
}

# Note: Using Rego's built-in lower() function directly
