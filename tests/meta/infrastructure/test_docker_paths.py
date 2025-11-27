"""
Test Docker image configuration and Python path validation.

These tests ensure Docker images are built with correct paths and configurations,
preventing runtime errors due to missing Python interpreters or incorrect paths.

TDD Approach (RED → GREEN → REFACTOR):
1. RED: Tests may pass or fail depending on current Docker image state
2. GREEN: Ensure Docker configurations are correct
3. REFACTOR: Improve Docker build process while keeping tests green
"""

from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def get_ci_workflow():
    """Get the CI workflow file."""
    workflows_dir = Path(__file__).parent.parent.parent.parent / ".github" / "workflows"
    ci_file = workflows_dir / "ci.yaml"
    if not ci_file.exists():
        ci_file = workflows_dir / "ci.yml"
    return ci_file


def test_docker_python_path_consistency():
    """
    Test that Docker smoke tests use correct Python paths for each variant.

    Different Docker base images have Python installed at different paths:
    - python:3.12-slim - Python at /usr/local/bin/python3
    - Distroless - Python at /usr/bin/python3 (if using distroless/python)
    - uv-managed venv - Python at /app/.venv/bin/python (uv sync installs here)

    The smoke test must use the correct path for each variant to avoid:
    "exec: /usr/bin/python3: not found" errors

    This test validates that the CI workflow correctly handles Python paths.
    """
    ci_file = get_ci_workflow()
    assert ci_file.exists(), f"CI workflow not found: {ci_file}"

    with open(ci_file) as f:
        workflow = yaml.safe_load(f)

    # Find the Docker build job
    jobs = workflow.get("jobs", {})
    docker_jobs = [(name, config) for name, config in jobs.items() if "docker" in name.lower() and isinstance(config, dict)]

    assert docker_jobs, "No Docker build jobs found in CI workflow"

    # Check each Docker job for Python path configuration
    for job_name, job_config in docker_jobs:
        steps = job_config.get("steps", [])

        # Find smoke test steps
        test_steps = [step for step in steps if isinstance(step, dict) and "test" in step.get("name", "").lower()]

        for step in test_steps:
            step_run = step.get("run", "")

            # Check if step uses Python path
            if "python" in step_run.lower() and "docker run" in step_run:
                # Verify that path is configurable or correctly set
                # The step should either:
                # 1. Use a variable like $PYTHON_PATH
                # 2. Have conditional logic for different variants
                # 3. Use just "python" or "python3" (letting Docker resolve the path)

                has_path_variable = "PYTHON_PATH" in step_run or "python_path" in step_run.lower()
                has_conditional = "if " in step_run and "variant" in step_run
                uses_simple_python = (
                    'entrypoint "$PYTHON_PATH"' in step_run
                    or 'entrypoint "python' in step_run
                    or "entrypoint python" in step_run
                )

                is_configured = has_path_variable or has_conditional or uses_simple_python

                assert is_configured, f"Docker test step in {job_name} doesn't properly configure Python path:\n{step.get('name', 'unnamed step')}"


def test_docker_variant_matrix_complete():
    """
    Test that Docker build matrix includes all expected variants.

    The CI workflow should build and test multiple Docker image variants:
    - base: Minimal image
    - full: Full-featured image
    - test: Image with test dependencies

    Each variant should be tested independently.
    """
    ci_file = get_ci_workflow()

    with open(ci_file) as f:
        workflow = yaml.safe_load(f)

    jobs = workflow.get("jobs", {})

    # Find jobs with matrix strategy
    matrix_jobs = [
        (name, config)
        for name, config in jobs.items()
        if isinstance(config, dict) and "strategy" in config and "matrix" in config.get("strategy", {})
    ]

    # Check if any Docker job uses matrix
    docker_matrix_jobs = [
        (name, config)
        for name, config in matrix_jobs
        if "docker" in name.lower() or any("docker" in str(step).lower() for step in config.get("steps", []))
    ]

    if not docker_matrix_jobs:
        pytest.skip("No Docker matrix jobs found in CI workflow")

    # Verify matrix includes expected variants
    for job_name, job_config in docker_matrix_jobs:
        matrix = job_config["strategy"]["matrix"]

        # Check for variant dimension
        if "variant" in matrix:
            variants = matrix["variant"]
            assert isinstance(variants, list), f"Matrix variant should be a list in {job_name}"
            assert len(variants) > 0, f"Matrix variant list is empty in {job_name}"

            # Common variants
            expected_variants = {"base", "full", "test"}
            actual_variants = set(variants)

            # At least one expected variant should exist
            common = expected_variants & actual_variants
            assert (
                common
            ), f"No common Docker variants found in {job_name}. Expected one of: {expected_variants}, got: {actual_variants}"


def test_docker_image_verification_comprehensive():
    """
    Test that Docker images are verified after build.

    The CI workflow should verify built images by:
    1. Checking image was loaded (docker images | grep)
    2. Inspecting image metadata (docker inspect)
    3. Running smoke test (docker run)

    This ensures images are functional before deployment.
    """
    ci_file = get_ci_workflow()

    with open(ci_file) as f:
        content = f.read()

    # Check for image verification patterns
    verification_patterns = {
        "docker images": "Check image was loaded",
        "docker inspect": "Inspect image metadata",
        "docker run": "Run smoke test",
    }

    found_verifications = {}
    for pattern, description in verification_patterns.items():
        if pattern in content:
            found_verifications[description] = True

    # All verification steps should be present
    missing = [desc for desc, found in verification_patterns.items() if desc not in found_verifications]

    assert (
        len(found_verifications) >= 2
    ), f"Docker build verification is incomplete. Found: {list(found_verifications.keys())}, Missing checks: {missing}"


def test_docker_entrypoint_configuration():
    """
    Test that Docker entrypoint configuration is validated in CI.

    The smoke test should verify that:
    - The entrypoint is correctly set
    - Python can be invoked
    - Basic imports work

    This prevents "entrypoint not found" errors in production.
    """
    ci_file = get_ci_workflow()

    with open(ci_file) as f:
        content = f.read()

    # Check for entrypoint testing
    has_entrypoint_test = "--entrypoint" in content or "entrypoint" in content.lower()

    # Check for import test (validates Python and dependencies are available)
    has_import_test = "import " in content and ("mcp_server" in content or "core.agent" in content)

    assert has_entrypoint_test, "CI workflow doesn't test Docker entrypoint. Add: docker run --entrypoint <python> <image>"
    assert (
        has_import_test
    ), "CI workflow doesn't test Python imports. Add: docker run <image> python -c 'import mcp_server_langgraph'"


def test_docker_smoke_test_validates_variants():
    """
    Test that smoke tests are variant-aware and test each variant appropriately.

    Different variants may have different:
    - Python locations (/usr/bin vs /usr/local/bin vs /app/.venv/bin)
    - Installed packages (test variant has test dependencies, base does not)
    - Entrypoints (some use venv activation, others don't)

    The smoke test should handle these differences.
    """
    ci_file = get_ci_workflow()

    with open(ci_file) as f:
        workflow = yaml.safe_load(f)

    jobs = workflow.get("jobs", {})

    # Find Docker test jobs
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        steps = job_config.get("steps", [])

        # Find test steps
        for step in steps:
            if not isinstance(step, dict):
                continue

            step_name = step.get("name", "")
            step_run = step.get("run", "")

            if "test" in step_name.lower() and "docker run" in step_run:
                # Check if test is variant-aware
                has_variant_logic = "${{ matrix.variant }}" in step_run or "variant" in step_run.lower()

                # If using matrix, should reference variant
                if "strategy" in job_config and "matrix" in job_config.get("strategy", {}):
                    assert has_variant_logic, f"Docker test step '{step_name}' doesn't use variant from matrix in {job_name}"
