#!/usr/bin/env python
"""Pre-generation hook for cookiecutter template validation."""

import re
import sys


def validate_project_slug(slug: str) -> bool:
    """Validate project slug is a valid Python module name."""
    pattern = r"^[a-z][a-z0-9_]*$"
    if not re.match(pattern, slug):
        print(f"ERROR: '{slug}' is not a valid Python module name!")
        print("Project slug must:")
        print("  - Start with a lowercase letter")
        print("  - Contain only lowercase letters, numbers, and underscores")
        print("  - Not contain hyphens or spaces")
        return False
    return True


def validate_github_username(username: str) -> bool:
    """Validate GitHub username format."""
    if not username or username == "yourusername":
        print("WARNING: Using default GitHub username 'yourusername'")
        print("You should update this in the generated files")
        return True

    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]){0,38}$"
    if not re.match(pattern, username):
        print(f"ERROR: '{username}' is not a valid GitHub username!")
        return False
    return True


def validate_email(email: str) -> bool:
    """Validate email format."""
    if email == "your.email@example.com":
        print("WARNING: Using default email")
        return True

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        print(f"ERROR: '{email}' is not a valid email address!")
        return False
    return True


def validate_configuration():
    """Validate cookiecutter configuration."""
    project_slug = "{{ cookiecutter.project_slug }}"
    github_username = "{{ cookiecutter.github_username }}"
    author_email = "{{ cookiecutter.author_email }}"

    print("Validating project configuration...")

    valid = True

    # Validate project slug
    if not validate_project_slug(project_slug):
        valid = False

    # Validate GitHub username
    if not validate_github_username(github_username):
        valid = False

    # Validate email
    if not validate_email(author_email):
        valid = False

    # Check for placeholder values
    if "{{ cookiecutter.author_name }}" == "Your Name":
        print("WARNING: Using default author name 'Your Name'")

    # Feature combination validation
    use_auth = "{{ cookiecutter.use_authentication }}" == "yes"
    use_authz = "{{ cookiecutter.use_authorization }}" == "yes"

    if use_authz and not use_auth:
        print("ERROR: Authorization requires authentication to be enabled!")
        valid = False

    observability = "{{ cookiecutter.observability_level }}"
    include_k8s = "{{ cookiecutter.include_kubernetes }}" == "yes"

    if include_k8s and observability == "minimal":
        print("WARNING: Kubernetes deployment with minimal observability is not recommended")

    if not valid:
        print("\n❌ Validation failed! Please fix the errors above.")
        sys.exit(1)

    print("✓ Configuration validated successfully!")


if __name__ == "__main__":
    validate_configuration()
