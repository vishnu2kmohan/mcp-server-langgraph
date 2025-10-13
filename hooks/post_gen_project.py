#!/usr/bin/env python
"""Post-generation hook to customize the generated project."""

import shutil
from pathlib import Path


def _remove_file(file_path: Path, message: str = None):
    """Helper to remove a file if it exists."""
    if file_path.exists():
        file_path.unlink()
        if message:
            print(f"✓ {message}")


def _remove_directory(dir_path: Path, message: str = None):
    """Helper to remove a directory if it exists."""
    if dir_path.exists():
        shutil.rmtree(dir_path)
        if message:
            print(f"✓ {message}")


def _cleanup_mcp_transports(project_root: Path):
    """Remove unused MCP transport files."""
    mcp_transports = "{{ cookiecutter.mcp_transports }}"
    if mcp_transports == "all":
        return

    if "stdio" not in mcp_transports:
        _remove_file(project_root / "mcp_server.py", "Removed mcp_server.py (stdio transport not selected)")

    if "http_sse" not in mcp_transports:
        _remove_file(project_root / "mcp_server_http.py", "Removed mcp_server_http.py (HTTP/SSE transport not selected)")

    if "streamable_http" not in mcp_transports:
        _remove_file(
            project_root / "mcp_server_streamable.py", "Removed mcp_server_streamable.py (StreamableHTTP transport not selected)"
        )


def _cleanup_authentication(project_root: Path):
    """Remove authentication files if disabled."""
    if "{{ cookiecutter.use_authentication }}" == "no":
        _remove_file(project_root / "auth.py", "Removed auth.py (authentication disabled)")


def _cleanup_authorization(project_root: Path):
    """Remove authorization files if disabled."""
    if "{{ cookiecutter.use_authorization }}" == "no" or "{{ cookiecutter.authorization_backend }}" == "none":
        _remove_file(project_root / "openfga_client.py", "Removed openfga_client.py (authorization disabled)")
        _remove_file(project_root / "setup_openfga.py", "Removed setup_openfga.py")
        _remove_file(project_root / "example_openfga_usage.py")


def _cleanup_secrets_manager(project_root: Path):
    """Remove secrets manager files if disabled."""
    if "{{ cookiecutter.use_secrets_manager }}" == "no" or "{{ cookiecutter.secrets_backend }}" == "env_only":
        _remove_file(project_root / "secrets_manager.py", "Removed secrets_manager.py (secrets manager disabled)")
        _remove_file(project_root / "setup_infisical.py", "Removed setup_infisical.py")


def _cleanup_kubernetes(project_root: Path):
    """Remove Kubernetes deployment files based on configuration."""
    if "{{ cookiecutter.include_kubernetes }}" == "no":
        _remove_directory(project_root / "kubernetes", "Removed kubernetes/ directory")
        _remove_directory(project_root / "helm", "Removed helm/ directory")
        _remove_directory(project_root / "kustomize", "Removed kustomize/ directory")
        _remove_file(project_root / "KUBERNETES_DEPLOYMENT.md")
    elif "{{ cookiecutter.kubernetes_flavor }}" != "both":
        flavor = "{{ cookiecutter.kubernetes_flavor }}"
        if flavor != "helm":
            _remove_directory(project_root / "helm", "Removed helm/ directory (not selected)")
        if flavor != "kustomize":
            _remove_directory(project_root / "kustomize", "Removed kustomize/ directory (not selected)")


def _cleanup_docker(project_root: Path):
    """Remove Docker files if disabled."""
    if "{{ cookiecutter.include_docker }}" == "no":
        _remove_file(project_root / "Dockerfile", "Removed Dockerfile")
        _remove_file(project_root / "docker-compose.yaml", "Removed docker-compose.yaml")
        _remove_file(project_root / ".dockerignore")


def _cleanup_cloudrun(project_root: Path):
    """Remove Cloud Run files if disabled."""
    if "{{ cookiecutter.include_cloudrun }}" == "no":
        _remove_directory(project_root / "cloudrun", "Removed cloudrun/ directory")
        _remove_file(project_root / "CLOUDRUN_DEPLOYMENT.md", "Removed CLOUDRUN_DEPLOYMENT.md")


def _cleanup_ci_cd(project_root: Path):
    """Remove CI/CD files based on platform selection."""
    if "{{ cookiecutter.include_ci_cd }}" == "no":
        _remove_directory(project_root / ".github" / "workflows", "Removed .github/workflows/")
        _remove_file(project_root / ".gitlab-ci.yml")
    elif "{{ cookiecutter.ci_platform }}" == "github_actions":
        _remove_file(project_root / ".gitlab-ci.yml", "Removed .gitlab-ci.yml")
    elif "{{ cookiecutter.ci_platform }}" == "gitlab_ci":
        _remove_directory(project_root / ".github" / "workflows", "Removed .github/workflows/")


def _cleanup_pre_commit(project_root: Path):
    """Remove pre-commit config if disabled."""
    if "{{ cookiecutter.include_pre_commit }}" == "no":
        _remove_file(project_root / ".pre-commit-config.yaml", "Removed .pre-commit-config.yaml")


def _cleanup_documentation(project_root: Path):
    """Remove documentation files based on configuration."""
    if "{{ cookiecutter.include_documentation }}" == "no":
        _remove_directory(project_root / "docs", "Removed docs/ directory")
        _remove_file(project_root / "mint.json")
    elif "{{ cookiecutter.documentation_format }}" != "mintlify":
        _remove_file(project_root / "mint.json")
        if (project_root / "docs").exists() and (project_root / "docs" / "getting-started").exists():
            _remove_directory(project_root / "docs")


def _cleanup_examples(project_root: Path):
    """Remove examples directory if disabled."""
    if "{{ cookiecutter.include_examples }}" == "no":
        _remove_directory(project_root / "examples", "Removed examples/ directory")


def _cleanup_observability(project_root: Path):
    """Remove observability files based on level."""
    observability = "{{ cookiecutter.observability_level }}"
    if observability == "minimal":
        _remove_directory(project_root / "grafana", "Removed grafana/ directory")
        _remove_directory(project_root / "monitoring", "Removed monitoring/ directory")
        _remove_file(project_root / "otel-collector-config.yaml")
    elif observability == "basic":
        _remove_directory(project_root / "grafana", "Removed grafana/ directory (basic observability)")


def remove_files_by_condition():
    """Remove files based on cookiecutter configuration."""
    project_root = Path.cwd()

    _cleanup_mcp_transports(project_root)
    _cleanup_authentication(project_root)
    _cleanup_authorization(project_root)
    _cleanup_secrets_manager(project_root)
    _cleanup_kubernetes(project_root)
    _cleanup_docker(project_root)
    _cleanup_cloudrun(project_root)
    _cleanup_ci_cd(project_root)
    _cleanup_pre_commit(project_root)
    _cleanup_documentation(project_root)
    _cleanup_examples(project_root)
    _cleanup_observability(project_root)


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
    print("   - README.md - Project overview")
    print("   - DEVELOPMENT.md - Development guide")
    if "{{ cookiecutter.use_authorization }}" == "yes":
        print("   - SECURITY_AUDIT.md - Security checklist")

    print("\n🔗 Helpful Links:")
    print(f"   - GitHub: https://github.com/{{ cookiecutter.github_username }}/{project_slug}")
    print("   - Documentation: README.md")

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
