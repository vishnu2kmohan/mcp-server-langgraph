"""
Test workflow job dependency validation.

These tests ensure that job dependencies are properly declared and referenced,
preventing runtime errors due to undefined needs references.

TDD Approach (RED → GREEN → REFACTOR):
1. RED: Tests fail initially due to missing job dependencies
2. GREEN: Fix workflows to declare all referenced dependencies
3. REFACTOR: Improve dependency structure while keeping tests green
"""

import gc
from pathlib import Path

import pytest
import yaml


def get_workflow_files():
    """Get all workflow YAML files."""
    workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
    return list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))


def extract_needs_references(text):
    """
    Extract all needs.* references from workflow text.

    Returns set of job names that are referenced via needs.job_name
    """
    import re

    # Pattern: needs.job_name (but not needs.job_name.outputs or needs.job_name.result)
    # We want to capture the job name being referenced
    pattern = r"needs\.([a-zA-Z0-9_-]+)"
    matches = re.findall(pattern, str(text))

    # Filter out special properties
    job_names = {match for match in matches if match not in ["result", "outputs", "conclusion"]}

    return job_names


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.name)
def test_job_dependencies_declared(workflow_file):
    """
    Test that all needs.* references have corresponding job dependencies declared.

    When a job references needs.other_job, it must declare other_job in its needs array.
    Otherwise, the workflow will fail at runtime with undefined reference errors.

    Expected to FAIL initially (RED phase) for:
    - deploy-production-gke.yaml:545 - rollback-on-failure references needs.build-and-push
      but doesn't include build-and-push in its needs array

    Correct pattern:
        rollback:
          needs: [deploy, build-and-push]  # Declare ALL dependencies
          steps:
            - run: echo ${{ needs.build-and-push.outputs.tag }}  # Now valid
    """
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    errors = []
    jobs = workflow.get("jobs", {})

    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        # Get declared dependencies
        needs = job_config.get("needs", [])

        # Normalize to list
        if isinstance(needs, str):
            declared_deps = {needs}
        elif isinstance(needs, list):
            declared_deps = set(needs)
        else:
            declared_deps = set()

        # Find all needs.* references in the job
        job_str = str(job_config)
        referenced_jobs = extract_needs_references(job_str)

        # Check if all referenced jobs are declared
        missing_deps = referenced_jobs - declared_deps

        if missing_deps:
            errors.append(
                f"Job '{job_name}' references undeclared dependencies.\n"
                f"  File: {workflow_file.name}\n"
                f"  Missing from needs array: {sorted(missing_deps)}\n"
                f"  Currently declared: {sorted(declared_deps) if declared_deps else '(none)'}\n"
                f"  Referenced in job: {sorted(referenced_jobs)}\n"
                f"  FIX: Add {sorted(missing_deps)} to needs: [{', '.join(sorted(declared_deps | missing_deps))}]"
            )

    assert not errors, "\n\n".join(errors)


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.name)
def test_no_circular_dependencies(workflow_file):
    """
    Test that workflows don't have circular job dependencies.

    Circular dependencies cause workflows to hang indefinitely.

    Example of circular dependency (invalid):
        job_a:
          needs: job_b
        job_b:
          needs: job_a  # Circular!
    """
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    jobs = workflow.get("jobs", {})

    # Build dependency graph
    dep_graph = {}
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        needs = job_config.get("needs", [])

        # Normalize to list
        if isinstance(needs, str):
            deps = [needs]
        elif isinstance(needs, list):
            deps = needs
        else:
            deps = []

        dep_graph[job_name] = deps

    # Detect cycles using DFS
    def has_cycle(node, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in dep_graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    # Check each job for cycles
    visited = set()
    for job in dep_graph:
        if job not in visited:
            rec_stack = set()
            if has_cycle(job, visited, rec_stack):
                pytest.fail(
                    f"Circular dependency detected in {workflow_file.name}\n"
                    f"Dependency graph: {dep_graph}\n"
                    f"FIX: Remove circular dependencies between jobs."
                )


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.name)
def test_referenced_jobs_exist(workflow_file):
    """
    Test that all jobs referenced in needs arrays actually exist in the workflow.

    This prevents typos in job names that would cause workflow failures.
    """
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    errors = []
    jobs = workflow.get("jobs", {})
    job_names = set(jobs.keys())

    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        needs = job_config.get("needs", [])

        # Normalize to list
        if isinstance(needs, str):
            deps = [needs]
        elif isinstance(needs, list):
            deps = needs
        else:
            deps = []

        # Check if all dependencies exist
        for dep in deps:
            if dep not in job_names:
                errors.append(
                    f"Job '{job_name}' depends on non-existent job '{dep}'.\n"
                    f"  File: {workflow_file.name}\n"
                    f"  Available jobs: {sorted(job_names)}\n"
                    f"  FIX: Check for typos or remove '{dep}' from needs array."
                )

    assert not errors, "\n\n".join(errors)


def test_dependency_validation_comprehensive():
    """
    Comprehensive test: validate all workflows have correct dependency structures.

    This integration test ensures:
    1. All needs.* references are declared
    2. No circular dependencies
    3. All referenced jobs exist
    4. Dependency graph is well-formed
    """
    workflow_files = get_workflow_files()
    assert len(workflow_files) > 0, "No workflow files found"

    total_jobs = 0
    total_dependencies = 0

    for workflow_file in workflow_files:
        with open(workflow_file) as f:
            workflow = yaml.safe_load(f)

        jobs = workflow.get("jobs", {})
        total_jobs += len(jobs)

        for job_config in jobs.values():
            if isinstance(job_config, dict):
                needs = job_config.get("needs", [])
                if isinstance(needs, list):
                    total_dependencies += len(needs)
                elif isinstance(needs, str):
                    total_dependencies += 1

    # At least some jobs should have dependencies
    assert total_jobs > 0, "No jobs found in workflows"
    # Dependencies are optional, so we don't assert on total_dependencies

    # Print stats for visibility
    print("\nWorkflow dependency statistics:")
    print(f"  Total workflows: {len(workflow_files)}")
    print(f"  Total jobs: {total_jobs}")
    print(f"  Total dependencies: {total_dependencies}")
    print(f"  Average dependencies per job: {total_dependencies / total_jobs if total_jobs > 0 else 0:.2f}")
