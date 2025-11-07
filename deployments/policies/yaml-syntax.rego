package main

# Detect inline comments in YAML string values
# This is particularly problematic in Istio/Gateway configurations

# VirtualService host validation
deny[msg] {
    input.kind == "VirtualService"

    host := input.spec.hosts[_]

    # Check if host string contains comment marker
    contains(host, "#")

    msg := sprintf(
        "VirtualService '%s' has inline comment in host string: '%s'. Move the comment to a separate line.",
        [input.metadata.name, host]
    )
}

# Gateway server host validation
deny[msg] {
    input.kind == "Gateway"

    server := input.spec.servers[_]
    host := server.hosts[_]

    contains(host, "#")

    msg := sprintf(
        "Gateway '%s' has inline comment in host string: '%s'. Move the comment to a separate line.",
        [input.metadata.name, host]
    )
}

# General warning for strings with TODO markers
warn[msg] {
    input.kind

    # Recursively check for TODO in string fields
    contains_todo_in_values(input)

    msg := sprintf(
        "%s '%s' contains TODO markers. Ensure all placeholder values are replaced before deployment.",
        [input.kind, input.metadata.name]
    )
}

# Helper: Recursively check for TODO in values
contains_todo_in_values(obj) {
    val := obj[_]
    is_string(val)
    contains(upper(val), "TODO")
}

contains_todo_in_values(obj) {
    val := obj[_]
    is_object(val)
    contains_todo_in_values(val)
}

contains_todo_in_values(obj) {
    val := obj[_]
    is_array(val)
    item := val[_]
    contains_todo_in_values(item)
}

# Detect unsubstituted template variables
deny[msg] {
    input.kind

    # Check for common unsubstituted variable patterns in critical fields
    check_unsubstituted_in_critical_fields(input)

    msg := sprintf(
        "%s '%s' contains unsubstituted variables (${...} or $(...)) in critical fields. Ensure all variables are replaced.",
        [input.kind, input.metadata.name]
    )
}

# Helper: Check for unsubstituted variables in critical fields
check_unsubstituted_in_critical_fields(obj) {
    # Check image names
    obj.spec.template.spec.containers[_].image
    img := obj.spec.template.spec.containers[_].image
    has_unsubstituted_var(img)
}

check_unsubstituted_in_critical_fields(obj) {
    # Check service hosts
    obj.kind == "VirtualService"
    host := obj.spec.hosts[_]
    has_unsubstituted_var(host)
}

# Helper: Check if string has unsubstituted variable
has_unsubstituted_var(str) {
    contains(str, "${")
}

has_unsubstituted_var(str) {
    contains(str, "$(")
}

# Validation for common YAML mistakes
warn[msg] {
    input.kind == "ConfigMap"
    data := input.data[_]

    # Check for common JSON syntax errors in ConfigMap data
    contains(data, "{{")
    not contains(data, "}}")

    msg := sprintf(
        "ConfigMap '%s' may have malformed template syntax (unmatched {{ braces).",
        [input.metadata.name]
    )
}

# Helper to convert string to uppercase
upper(s) = u {
    u := upper(s)
}
