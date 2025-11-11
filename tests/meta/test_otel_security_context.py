"""
Test OpenTelemetry Collector security context configuration.

This test validates the fix for Trivy security findings:
- AVD-KSV-0014 (HIGH): Container should set readOnlyRootFilesystem
- AVD-KSV-0118 (HIGH): Container using default security context
- AVD-KSV-0118 (HIGH): Deployment using default security context (allows root)

The OTel collector deployment must have:
- Pod-level security context (runAsNonRoot, runAsUser, fsGroup, seccomp)
- Container-level security context (readOnlyRootFilesystem, drop ALL capabilities)
- tmpfs volumes for writable directories (/tmp, /home/otelcol)

Reference: Deploy to GKE Staging workflow failures with 5 HIGH Trivy findings
Verified UID: 10001 (from official otel/opentelemetry-collector-contrib:0.137.0 image)
"""

import subprocess
from pathlib import Path

import pytest
import yaml


def test_otel_deployment_has_pod_security_context():
    """
    Verify that OTel collector deployment has pod-level security context.

    Required for Trivy AVD-KSV-0118 compliance:
    - runAsNonRoot: true
    - runAsUser: 10001 (verified from official image)
    - fsGroup: 10001
    - seccompProfile.type: RuntimeDefault
    """
    deployment_file = Path(
        "/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "deployments/base/otel-collector-deployment.yaml"
    )

    assert deployment_file.exists(), f"OTel deployment not found: {deployment_file}"

    with open(deployment_file) as f:
        # File may contain multiple YAML documents
        docs = list(yaml.safe_load_all(f))
        # Find the Deployment document
        otel_deployment = next((doc for doc in docs if doc and doc.get("kind") == "Deployment"), None)

    assert otel_deployment is not None, "Deployment document not found in otel-collector-deployment.yaml"

    # Navigate to pod spec
    pod_spec = otel_deployment.get("spec", {}).get("template", {}).get("spec", {})

    assert pod_spec, "Pod spec not found in deployment"

    # Check for pod-level securityContext
    security_context = pod_spec.get("securityContext")

    assert security_context is not None, (
        "Pod-level securityContext not found in OTel deployment.\n"
        "\n"
        "Required for Trivy AVD-KSV-0118 compliance.\n"
        "\n"
        "Expected:\n"
        "spec:\n"
        "  template:\n"
        "    spec:\n"
        "      securityContext:\n"
        "        runAsNonRoot: true\n"
        "        runAsUser: 10001\n"
        "        fsGroup: 10001\n"
        "        seccompProfile:\n"
        "          type: RuntimeDefault\n"
        "\n"
        f"Current pod spec keys: {list(pod_spec.keys())}"
    )

    # Validate runAsNonRoot
    assert security_context.get("runAsNonRoot") is True, "Pod securityContext must set runAsNonRoot: true"

    # Validate runAsUser (10001 from official image)
    assert security_context.get("runAsUser") == 10001, (
        f"Pod securityContext must set runAsUser: 10001 (verified from official image), "
        f"got: {security_context.get('runAsUser')}"
    )

    # Validate fsGroup
    assert (
        security_context.get("fsGroup") == 10001
    ), f"Pod securityContext must set fsGroup: 10001, got: {security_context.get('fsGroup')}"

    # Validate seccomp profile
    seccomp = security_context.get("seccompProfile")
    assert seccomp is not None, "Pod securityContext must specify seccompProfile"
    assert seccomp.get("type") == "RuntimeDefault", f"seccompProfile.type must be RuntimeDefault, got: {seccomp.get('type')}"


def test_otel_deployment_has_container_security_context():
    """
    Verify that OTel collector container has security context.

    Required for Trivy AVD-KSV-0014 and AVD-KSV-0118 compliance:
    - allowPrivilegeEscalation: false
    - readOnlyRootFilesystem: true
    - runAsNonRoot: true
    - runAsUser: 10001
    - capabilities.drop: [ALL]
    """
    deployment_file = Path(
        "/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "deployments/base/otel-collector-deployment.yaml"
    )

    with open(deployment_file) as f:
        docs = list(yaml.safe_load_all(f))
        otel_deployment = next((doc for doc in docs if doc and doc.get("kind") == "Deployment"), None)

    assert otel_deployment is not None, "Deployment not found"

    # Find otel-collector container
    containers = otel_deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    otel_container = None
    for container in containers:
        if container.get("name") == "otel-collector":
            otel_container = container
            break

    assert otel_container is not None, (
        "otel-collector container not found in deployment.\n" f"Available containers: {[c.get('name') for c in containers]}"
    )

    # Check for container-level securityContext
    security_context = otel_container.get("securityContext")

    assert security_context is not None, (
        "Container-level securityContext not found for otel-collector.\n"
        "\n"
        "Required for Trivy AVD-KSV-0014 and AVD-KSV-0118 compliance.\n"
        "\n"
        "Expected:\n"
        "  securityContext:\n"
        "    allowPrivilegeEscalation: false\n"
        "    readOnlyRootFilesystem: true\n"
        "    runAsNonRoot: true\n"
        "    runAsUser: 10001\n"
        "    capabilities:\n"
        "      drop: [ALL]\n"
        "\n"
        f"Current container keys: {list(otel_container.keys())}"
    )

    # Validate each security setting
    assert (
        security_context.get("allowPrivilegeEscalation") is False
    ), "Container securityContext must set allowPrivilegeEscalation: false"

    assert (
        security_context.get("readOnlyRootFilesystem") is True
    ), "Container securityContext must set readOnlyRootFilesystem: true (Trivy AVD-KSV-0014)"

    assert security_context.get("runAsNonRoot") is True, "Container securityContext must set runAsNonRoot: true"

    assert (
        security_context.get("runAsUser") == 10001
    ), f"Container securityContext must set runAsUser: 10001, got: {security_context.get('runAsUser')}"

    # Validate capabilities
    capabilities = security_context.get("capabilities")
    assert capabilities is not None, "Container securityContext must specify capabilities"

    drop_caps = capabilities.get("drop", [])
    assert "ALL" in drop_caps, f"Container securityContext must drop ALL capabilities, got: {drop_caps}"


def test_otel_has_readonly_root_filesystem():
    """
    Verify that readOnlyRootFilesystem is set to true.

    This is the specific finding from Trivy AVD-KSV-0014:
    "Container 'otel-collector' should set 'securityContext.readOnlyRootFilesystem' to true"
    """
    deployment_file = Path(
        "/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "deployments/base/otel-collector-deployment.yaml"
    )

    with open(deployment_file) as f:
        docs = list(yaml.safe_load_all(f))
        otel_deployment = next((doc for doc in docs if doc and doc.get("kind") == "Deployment"), None)

    assert otel_deployment is not None, "Deployment not found"

    containers = otel_deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    otel_container = next((c for c in containers if c.get("name") == "otel-collector"), None)
    assert otel_container is not None

    readonly_filesystem = otel_container.get("securityContext", {}).get("readOnlyRootFilesystem")

    assert readonly_filesystem is True, (
        "Trivy AVD-KSV-0014: Container 'otel-collector' must set "
        "'securityContext.readOnlyRootFilesystem' to true.\n"
        "\n"
        "This prevents modification of the root filesystem, reducing attack surface.\n"
        f"Current value: {readonly_filesystem}"
    )


def test_otel_runs_as_nonroot():
    """
    Verify that OTel collector runs as non-root user.

    Both pod and container levels must specify runAsNonRoot: true.
    This addresses Trivy AVD-KSV-0118 finding about default security context.
    """
    deployment_file = Path(
        "/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "deployments/base/otel-collector-deployment.yaml"
    )

    with open(deployment_file) as f:
        docs = list(yaml.safe_load_all(f))
        otel_deployment = next((doc for doc in docs if doc and doc.get("kind") == "Deployment"), None)

    assert otel_deployment is not None, "Deployment not found"

    pod_spec = otel_deployment.get("spec", {}).get("template", {}).get("spec", {})

    # Check pod-level runAsNonRoot
    pod_run_as_nonroot = pod_spec.get("securityContext", {}).get("runAsNonRoot")
    assert pod_run_as_nonroot is True, "Pod-level securityContext must set runAsNonRoot: true"

    # Check container-level runAsNonRoot
    containers = pod_spec.get("containers", [])
    otel_container = next((c for c in containers if c.get("name") == "otel-collector"), None)

    container_run_as_nonroot = otel_container.get("securityContext", {}).get("runAsNonRoot")
    assert container_run_as_nonroot is True, "Container-level securityContext must set runAsNonRoot: true"


def test_otel_has_tmpfs_volumes():
    """
    Verify that OTel collector has tmpfs volumes for writable directories.

    When readOnlyRootFilesystem is true, OTel needs writable volumes for:
    - /tmp - Temporary files
    - /home/otelcol - OTel collector home directory

    These should be emptyDir volumes (tmpfs in memory).
    """
    deployment_file = Path(
        "/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "deployments/base/otel-collector-deployment.yaml"
    )

    with open(deployment_file) as f:
        docs = list(yaml.safe_load_all(f))
        otel_deployment = next((doc for doc in docs if doc and doc.get("kind") == "Deployment"), None)

    assert otel_deployment is not None, "Deployment not found"

    pod_spec = otel_deployment.get("spec", {}).get("template", {}).get("spec", {})

    # Check volumes
    volumes = pod_spec.get("volumes", [])
    volume_names = [v.get("name") for v in volumes]

    assert "tmp" in volume_names or "otel-tmp" in volume_names, (
        "Missing tmpfs volume for /tmp directory.\n"
        "\n"
        "When readOnlyRootFilesystem is true, OTel needs a writable /tmp.\n"
        "\n"
        "Expected volume:\n"
        "  - name: tmp\n"
        "    emptyDir: {}\n"
        "\n"
        f"Current volumes: {volume_names}"
    )

    assert "home" in volume_names or "otel-home" in volume_names, (
        "Missing tmpfs volume for /home/otelcol directory.\n"
        "\n"
        "When readOnlyRootFilesystem is true, OTel needs a writable home directory.\n"
        "\n"
        "Expected volume:\n"
        "  - name: home\n"
        "    emptyDir: {}\n"
        "\n"
        f"Current volumes: {volume_names}"
    )

    # Check volume mounts
    containers = pod_spec.get("containers", [])
    otel_container = next((c for c in containers if c.get("name") == "otel-collector"), None)

    volume_mounts = otel_container.get("volumeMounts", [])
    mount_paths = [vm.get("mountPath") for vm in volume_mounts]

    # Checking for volume mount path "/tmp", not creating temp file
    assert "/tmp" in mount_paths, "Missing volumeMount for /tmp directory.\n" f"Current mounts: {mount_paths}"  # nosec B108

    assert "/home/otelcol" in mount_paths or "/home" in mount_paths, (
        "Missing volumeMount for /home/otelcol or /home directory.\n" f"Current mounts: {mount_paths}"
    )


def test_otel_drops_all_capabilities():
    """
    Verify that OTel collector drops all Linux capabilities.

    Security best practice: Drop all capabilities unless specifically needed.
    OTel collector doesn't need any special capabilities.
    """
    deployment_file = Path(
        "/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "deployments/base/otel-collector-deployment.yaml"
    )

    with open(deployment_file) as f:
        docs = list(yaml.safe_load_all(f))
        otel_deployment = next((doc for doc in docs if doc and doc.get("kind") == "Deployment"), None)

    assert otel_deployment is not None, "Deployment not found"

    containers = otel_deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    otel_container = next((c for c in containers if c.get("name") == "otel-collector"), None)

    capabilities = otel_container.get("securityContext", {}).get("capabilities", {})

    assert capabilities, "Container securityContext must specify capabilities"

    drop_caps = capabilities.get("drop", [])

    assert "ALL" in drop_caps, (
        "Container securityContext must drop ALL capabilities.\n"
        "\n"
        "Security best practice: Drop all Linux capabilities unless specifically needed.\n"
        "OTel collector doesn't require any special capabilities.\n"
        "\n"
        f"Current capabilities.drop: {drop_caps}"
    )


def test_rendered_staging_manifest_has_otel_security_context():
    """
    Verify that the rendered staging manifest includes OTel security contexts.

    This is an integration test that renders the complete Kustomize overlay
    and validates that the security contexts are present in the final output
    that will be deployed to GKE.
    """
    # Render the staging overlay
    result = subprocess.run(
        ["kubectl", "kustomize", "deployments/overlays/staging-gke"],
        capture_output=True,
        text=True,
        cwd="/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph",
    )

    assert result.returncode == 0, f"kubectl kustomize failed: {result.stderr}"

    # Parse rendered YAML
    rendered_docs = list(yaml.safe_load_all(result.stdout))

    # Find OTel collector deployment
    otel_deployment = None
    for doc in rendered_docs:
        if doc is None:
            continue
        if doc.get("kind") == "Deployment" and doc.get("metadata", {}).get("name") == "staging-otel-collector":
            otel_deployment = doc
            break

    assert otel_deployment is not None, (
        "OTel collector deployment not found in rendered staging manifests.\n"
        "Expected 'staging-otel-collector' (with namePrefix from kustomization.yaml)"
    )

    # Validate pod-level security context
    pod_security_context = otel_deployment.get("spec", {}).get("template", {}).get("spec", {}).get("securityContext", {})

    assert pod_security_context.get("runAsNonRoot") is True, "Rendered manifest missing pod-level runAsNonRoot: true"

    # Validate container-level security context
    containers = otel_deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    otel_container = next((c for c in containers if "otel-collector" in c.get("name", "")), None)

    assert otel_container is not None, "OTel collector container not found"

    container_security_context = otel_container.get("securityContext", {})

    assert (
        container_security_context.get("readOnlyRootFilesystem") is True
    ), "Rendered manifest missing container-level readOnlyRootFilesystem: true (Trivy AVD-KSV-0014)"

    assert (
        container_security_context.get("runAsNonRoot") is True
    ), "Rendered manifest missing container-level runAsNonRoot: true"

    capabilities = container_security_context.get("capabilities", {})
    assert "ALL" in capabilities.get("drop", []), "Rendered manifest missing capabilities.drop: [ALL]"
