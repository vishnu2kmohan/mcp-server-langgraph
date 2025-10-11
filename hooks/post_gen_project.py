#!/usr/bin/env python
"""Post-generation hook to customize the generated project."""

import os
import shutil
from pathlib import Path


def remove_files_by_condition():
    """Remove files based on cookiecutter configuration."""
    project_root = Path.cwd()

    # MCP Transport cleanup
    mcp_transports = "{{ cookiecutter.mcp_transports }}"
    if mcp_transports != "all":
        if "stdio" not in mcp_transports and (project_root / "mcp_server.py").exists():
            (project_root / "mcp_server.py").unlink()
            print("✓ Removed mcp_server.py (stdio transport not selected)")

        if "http_sse" not in mcp_transports and (project_root / "mcp_server_http.py").exists():
            (project_root / "mcp_server_http.py").unlink()
            print("✓ Removed mcp_server_http.py (HTTP/SSE transport not selected)")

        if "streamable_http" not in mcp_transports and (project_root / "mcp_server_streamable.py").exists():
            (project_root / "mcp_server_streamable.py").unlink()
            print("✓ Removed mcp_server_streamable.py (StreamableHTTP transport not selected)")

    # Authentication cleanup
    if "{{ cookiecutter.use_authentication }}" == "no":
        if (project_root / "auth.py").exists():
            (project_root / "auth.py").unlink()
            print("✓ Removed auth.py (authentication disabled)")

    # Authorization cleanup
    if "{{ cookiecutter.use_authorization }}" == "no" or "{{ cookiecutter.authorization_backend }}" == "none":
        if (project_root / "openfga_client.py").exists():
            (project_root / "openfga_client.py").unlink()
            print("✓ Removed openfga_client.py (authorization disabled)")
        if (project_root / "setup_openfga.py").exists():
            (project_root / "setup_openfga.py").unlink()
            print("✓ Removed setup_openfga.py")
        if (project_root / "example_openfga_usage.py").exists():
            (project_root / "example_openfga_usage.py").unlink()

    # Secrets manager cleanup
    if "{{ cookiecutter.use_secrets_manager }}" == "no" or "{{ cookiecutter.secrets_backend }}" == "env_only":
        if (project_root / "secrets_manager.py").exists():
            (project_root / "secrets_manager.py").unlink()
            print("✓ Removed secrets_manager.py (secrets manager disabled)")
        if (project_root / "setup_infisical.py").exists():
            (project_root / "setup_infisical.py").unlink()
            print("✓ Removed setup_infisical.py")

    # Kubernetes cleanup
    if "{{ cookiecutter.include_kubernetes }}" == "no":
        if (project_root / "kubernetes").exists():
            shutil.rmtree(project_root / "kubernetes")
            print("✓ Removed kubernetes/ directory")
        if (project_root / "helm").exists():
            shutil.rmtree(project_root / "helm")
            print("✓ Removed helm/ directory")
        if (project_root / "kustomize").exists():
            shutil.rmtree(project_root / "kustomize")
            print("✓ Removed kustomize/ directory")
        if (project_root / "KUBERNETES_DEPLOYMENT.md").exists():
            (project_root / "KUBERNETES_DEPLOYMENT.md").unlink()

    elif "{{ cookiecutter.kubernetes_flavor }}" != "both":
        flavor = "{{ cookiecutter.kubernetes_flavor }}"
        if flavor != "helm" and (project_root / "helm").exists():
            shutil.rmtree(project_root / "helm")
            print("✓ Removed helm/ directory (not selected)")
        if flavor != "kustomize" and (project_root / "kustomize").exists():
            shutil.rmtree(project_root / "kustomize")
            print("✓ Removed kustomize/ directory (not selected)")

    # Docker cleanup
    if "{{ cookiecutter.include_docker }}" == "no":
        if (project_root / "Dockerfile").exists():
            (project_root / "Dockerfile").unlink()
            print("✓ Removed Dockerfile")
        if (project_root / "docker-compose.yaml").exists():
            (project_root / "docker-compose.yaml").unlink()
            print("✓ Removed docker-compose.yaml")
        if (project_root / ".dockerignore").exists():
            (project_root / ".dockerignore").unlink()

    # Cloud Run cleanup
    if "{{ cookiecutter.include_cloudrun }}" == "no":
        if (project_root / "cloudrun").exists():
            shutil.rmtree(project_root / "cloudrun")
            print("✓ Removed cloudrun/ directory")
        if (project_root / "CLOUDRUN_DEPLOYMENT.md").exists():
            (project_root / "CLOUDRUN_DEPLOYMENT.md").unlink()
            print("✓ Removed CLOUDRUN_DEPLOYMENT.md")

    # CI/CD cleanup
    if "{{ cookiecutter.include_ci_cd }}" == "no":
        if (project_root / ".github" / "workflows").exists():
            shutil.rmtree(project_root / ".github" / "workflows")
            print("✓ Removed .github/workflows/")
        if (project_root / ".gitlab-ci.yml").exists():
            (project_root / ".gitlab-ci.yml").unlink()

    elif "{{ cookiecutter.ci_platform }}" == "github_actions":
        if (project_root / ".gitlab-ci.yml").exists():
            (project_root / ".gitlab-ci.yml").unlink()
            print("✓ Removed .gitlab-ci.yml")

    elif "{{ cookiecutter.ci_platform }}" == "gitlab_ci":
        if (project_root / ".github" / "workflows").exists():
            shutil.rmtree(project_root / ".github" / "workflows")
            print("✓ Removed .github/workflows/")

    # Pre-commit cleanup
    if "{{ cookiecutter.include_pre_commit }}" == "no":
        if (project_root / ".pre-commit-config.yaml").exists():
            (project_root / ".pre-commit-config.yaml").unlink()
            print("✓ Removed .pre-commit-config.yaml")

    # Documentation cleanup
    if "{{ cookiecutter.include_documentation }}" == "no":
        if (project_root / "docs").exists():
            shutil.rmtree(project_root / "docs")
            print("✓ Removed docs/ directory")
        if (project_root / "mint.json").exists():
            (project_root / "mint.json").unlink()

    elif "{{ cookiecutter.documentation_format }}" != "mintlify":
        if (project_root / "mint.json").exists():
            (project_root / "mint.json").unlink()
        if (project_root / "docs").exists() and (project_root / "docs" / "getting-started").exists():
            # Remove Mintlify-specific docs
            shutil.rmtree(project_root / "docs")

    # Examples cleanup
    if "{{ cookiecutter.include_examples }}" == "no":
        if (project_root / "examples").exists():
            shutil.rmtree(project_root / "examples")
            print("✓ Removed examples/ directory")

    # Observability cleanup
    observability = "{{ cookiecutter.observability_level }}"
    if observability == "minimal":
        if (project_root / "grafana").exists():
            shutil.rmtree(project_root / "grafana")
            print("✓ Removed grafana/ directory")
        if (project_root / "monitoring").exists():
            shutil.rmtree(project_root / "monitoring")
            print("✓ Removed monitoring/ directory")
        if (project_root / "otel-collector-config.yaml").exists():
            (project_root / "otel-collector-config.yaml").unlink()

    elif observability == "basic":
        if (project_root / "grafana").exists():
            shutil.rmtree(project_root / "grafana")
            print("✓ Removed grafana/ directory (basic observability)")


def create_initial_git():
    """Initialize git repository if requested."""
    if "{{ cookiecutter.project_visibility }}" in ["public", "private"]:
        import subprocess

        try:
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit from mcp-server-langgraph template"], check=True, capture_output=True
            )
            print("✓ Initialized git repository with initial commit")
        except subprocess.CalledProcessError:
            print("⚠ Could not initialize git repository (git may not be installed)")
        except FileNotFoundError:
            print("⚠ Git not found, skipping repository initialization")


def print_next_steps():
    """Print next steps for the user."""
    project_name = "{{ cookiecutter.project_name }}"
    project_slug = "{{ cookiecutter.project_slug }}"
    mcp_transports = "{{ cookiecutter.mcp_transports }}"
    use_docker = "{{ cookiecutter.include_docker }}" == "yes"
    use_k8s = "{{ cookiecutter.include_kubernetes }}" == "yes"

    print("\n" + "=" * 70)
    print(f"🎉 Successfully generated: {project_name}")
    print("=" * 70)

    print("\n📋 Next Steps:\n")

    print("1. Navigate to your project:")
    print(f"   cd {project_slug}")

    print("\n2. Create virtual environment:")
    print("   python -m venv venv")
    print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")

    print("\n3. Install dependencies:")
    print("   pip install -r requirements.txt")

    if use_docker:
        print("\n4. Start infrastructure:")
        print("   docker-compose up -d")

    print("\n5. Configure environment:")
    print("   cp .env.example .env")
    print("   # Edit .env with your configuration")

    if "{{ cookiecutter.use_authorization }}" == "yes" and "{{ cookiecutter.authorization_backend }}" == "openfga":
        print("\n6. Setup OpenFGA:")
        print("   python setup_openfga.py")
        print("   # Add OPENFGA_STORE_ID and OPENFGA_MODEL_ID to .env")

    print("\n7. Run your MCP server:")
    if "stdio" in mcp_transports or mcp_transports == "all":
        print("   python mcp_server.py  # stdio transport")
    if "streamable_http" in mcp_transports or mcp_transports == "all":
        print("   python mcp_server_streamable.py  # StreamableHTTP")
    if "http_sse" in mcp_transports or mcp_transports == "all":
        print("   python mcp_server_http.py  # HTTP/SSE")

    print("\n8. Run tests:")
    print("   pytest -v")

    if use_k8s:
        print("\n📦 Kubernetes Deployment:")
        print("   See KUBERNETES_DEPLOYMENT.md for deployment instructions")

    if "{{ cookiecutter.include_cloudrun }}" == "yes":
        print("\n☁️  Google Cloud Run Deployment:")
        print("   See CLOUDRUN_DEPLOYMENT.md for deployment instructions")
        print("   Quick start: cd cloudrun && ./deploy.sh --setup")

    print("\n📚 Documentation:")
    print(f"   - README.md - Project overview")
    print(f"   - DEVELOPMENT.md - Development guide")
    if "{{ cookiecutter.use_authorization }}" == "yes":
        print(f"   - SECURITY_AUDIT.md - Security checklist")

    print("\n🔗 Helpful Links:")
    print(f"   - GitHub: https://github.com/{{ cookiecutter.github_username }}/{project_slug}")
    print(f"   - Documentation: README.md")

    print("\n" + "=" * 70)
    print("Happy coding! 🚀")
    print("=" * 70 + "\n")


def main():
    """Main post-generation hook."""
    print("\n🔧 Customizing your project...\n")

    remove_files_by_condition()
    create_initial_git()
    print_next_steps()


if __name__ == "__main__":
    main()
