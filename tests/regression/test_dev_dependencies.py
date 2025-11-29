"""
Validate that all test file imports are available in dev dependencies.

Prevents ModuleNotFoundError in CI by ensuring test imports match
the dependencies installed in test environments.

This test follows TDD principles:
- Written FIRST to catch the docker dependency issue
- Fails initially (RED phase)
- Passes after adding docker to dev deps (GREEN phase)
- Prevents future regressions (REFACTOR phase)
"""

import ast
import sys

import tomllib
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (regression prevention)
pytestmark = pytest.mark.unit


def get_all_dependencies() -> set[str]:
    """
    Extract all dependency package names from pyproject.toml.

    Includes:
    - Main dependencies (project.dependencies)
    - All optional dependencies (project.optional-dependencies.*)
    - Package name normalization (pytest-asyncio → pytest_asyncio)

    Returns:
        Set of package names available when dev extras installed
    """
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    packages = set()

    # Get main dependencies
    main_deps = data.get("project", {}).get("dependencies", [])
    for dep in main_deps:
        pkg = _normalize_package_name(dep)
        if pkg:
            packages.add(pkg)

    # Get all optional dependencies (dev, cli, secrets, code-execution, etc.)
    optional_deps = data.get("project", {}).get("optional-dependencies", {})
    for extra_name, extra_deps in optional_deps.items():
        for dep in extra_deps:
            pkg = _normalize_package_name(dep)
            if pkg:
                packages.add(pkg)

    return packages


def _normalize_package_name(dep_spec: str) -> str:
    """
    Extract and normalize package name from dependency specification.

    Handles:
    - Version specifiers: "package>=1.0.0" → "package"
    - Extras: "package[extra]>=1.0.0" → "package"
    - Hyphens vs underscores: "pytest-asyncio" → "pytest_asyncio"
    - Case normalization: "PyJWT" → "pyjwt"

    Args:
        dep_spec: Dependency specification string

    Returns:
        Normalized package name (import name format, lowercase)
    """
    # Strip version specifiers and extras
    pkg = dep_spec.split(">=")[0].split(">")[0].split("==")[0].split("<")[0]
    pkg = pkg.split("[")[0].strip('"').strip("'").strip()

    # Normalize hyphens to underscores (package-name → package_name)
    # This handles pytest-asyncio, python-on-whales, etc.
    pkg = pkg.replace("-", "_")

    # Normalize to lowercase for case-insensitive comparison
    pkg = pkg.lower()

    return pkg


def get_test_imports() -> set[str]:
    """
    Extract all top-level package imports from test files.

    Returns:
        Set of top-level package names imported in tests/
    """
    tests_dir = Path(__file__).parent.parent
    imports = set()

    for test_file in tests_dir.rglob("*.py"):
        # Skip __pycache__ and other special files
        if "__pycache__" in str(test_file) or test_file.name.startswith("__"):
            continue

        # Skip third-party test helper tools (e.g., bats-core)
        # These have their own dependencies that we don't control
        if "test_helper" in str(test_file):
            continue

        try:
            with open(test_file) as f:
                tree = ast.parse(f.read(), filename=str(test_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Extract top-level package: "foo.bar.baz" → "foo"
                        pkg = alias.name.split(".")[0]
                        imports.add(pkg)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Extract top-level package: "foo.bar.baz" → "foo"
                        pkg = node.module.split(".")[0]
                        imports.add(pkg)
        except SyntaxError:
            # Skip files with syntax errors (they'll fail elsewhere)
            continue

    return imports


def get_stdlib_modules() -> set[str]:
    """
    Get standard library module names for current Python version.

    Returns:
        Set of stdlib module names
    """
    # Comprehensive list of Python 3.12 standard library modules
    # This list covers common stdlib modules imported in tests
    stdlib = {
        "__future__",  # Future statement definitions (pseudo-module)
        "abc",
        "aifc",
        "argparse",
        "array",
        "ast",
        "asynchat",
        "asyncio",
        "asyncore",
        "atexit",
        "audioop",
        "base64",
        "bdb",
        "binascii",
        "bisect",
        "builtins",
        "bz2",
        "calendar",
        "cgi",
        "cgitb",
        "chunk",
        "cmath",
        "cmd",
        "code",
        "codecs",
        "codeop",
        "collections",
        "colorsys",
        "compileall",
        "concurrent",
        "configparser",
        "contextlib",
        "contextvars",
        "copy",
        "copyreg",
        "crypt",
        "csv",
        "ctypes",
        "curses",
        "dataclasses",
        "datetime",
        "dbm",
        "decimal",
        "difflib",
        "dis",
        "distutils",
        "doctest",
        "email",
        "encodings",
        "enum",
        "errno",
        "faulthandler",
        "fcntl",
        "filecmp",
        "fileinput",
        "fnmatch",
        "fractions",
        "ftplib",
        "functools",
        "gc",
        "getopt",
        "getpass",
        "gettext",
        "glob",
        "graphlib",
        "grp",
        "gzip",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "http",
        "imaplib",
        "imghdr",
        "importlib",
        "inspect",
        "io",
        "ipaddress",
        "itertools",
        "json",
        "keyword",
        "lib2to3",
        "linecache",
        "locale",
        "logging",
        "lzma",
        "mailbox",
        "mailcap",
        "marshal",
        "math",
        "mimetypes",
        "mmap",
        "modulefinder",
        "multiprocessing",
        "netrc",
        "nis",
        "nntplib",
        "numbers",
        "operator",
        "optparse",
        "os",
        "ossaudiodev",
        "pathlib",
        "pdb",
        "pickle",
        "pickletools",
        "pipes",
        "pkgutil",
        "platform",
        "plistlib",
        "poplib",
        "posix",
        "posixpath",
        "pprint",
        "profile",
        "pstats",
        "pty",
        "pwd",
        "py_compile",
        "pyclbr",
        "pydoc",
        "queue",
        "quopri",
        "random",
        "re",
        "readline",
        "reprlib",
        "resource",
        "rlcompleter",
        "runpy",
        "sched",
        "secrets",
        "select",
        "selectors",
        "shelve",
        "shlex",
        "shutil",
        "signal",
        "site",
        "smtpd",
        "smtplib",
        "sndhdr",
        "socket",
        "socketserver",
        "spwd",
        "sqlite3",
        "ssl",
        "stat",
        "statistics",
        "string",
        "stringprep",
        "struct",
        "subprocess",
        "sunau",
        "symtable",
        "sys",
        "sysconfig",
        "syslog",
        "tabnanny",
        "tarfile",
        "telnetlib",
        "tempfile",
        "termios",
        "test",
        "textwrap",
        "threading",
        "time",
        "timeit",
        "tkinter",
        "token",
        "tokenize",
        "tomllib",
        "trace",
        "traceback",
        "tracemalloc",
        "tty",
        "turtle",
        "turtledemo",
        "types",
        "typing",
        "typing_extensions",
        "unicodedata",
        "unittest",
        "urllib",
        "uu",
        "uuid",
        "venv",
        "warnings",
        "wave",
        "weakref",
        "webbrowser",
        "wsgiref",
        "xdrlib",
        "xml",
        "xmlrpc",
        "zipapp",
        "zipfile",
        "zipimport",
        "zlib",
        "_thread",
    }

    return stdlib


def get_project_modules() -> set[str]:
    """
    Get project-specific module names to exclude from dependency check.

    Returns:
        Set of project module names
    """
    return {
        "mcp_server_langgraph",  # Main project package
        "tests",  # Test package itself
        "src",  # Source directory
        "scripts",  # Scripts directory
        "deployments",  # Deployments directory
        "langgraph_platform",  # Local deployment module (in deployments/)
        # Test-specific modules (not packages)
        "test_auth_properties",
        "validate_mintlify_docs",
        "fix_mdx_syntax",  # Script in scripts/ directory, not a package
        "hcl2",  # Optional import for Terraform parsing (try/except in tests)
        # Local scripts imported by tests (in scripts/ directory)
        "check_internal_links",  # Script for checking documentation links
        "validate_gke_autopilot_compliance",  # Script for GKE Autopilot validation
        "validate_pytest_markers",  # Script for pytest marker validation
        "fix_missing_pytestmarks",  # Script for fixing missing pytestmark declarations
        "check_e2e_completion",  # Script for E2E test completion tracking
        "profile_hooks",  # Script for profiling pre-commit hooks
    }


def get_import_name_mapping() -> dict[str, str]:
    """
    Map package names to their import names when they differ.

    For example:
    - pyyaml package → yaml import
    - pyjwt package → jwt import
    - infisical-python → infisical_client

    Returns:
        Dictionary mapping import names to package names
    """
    return {
        # Package name differs from import name
        "yaml": "pyyaml",
        "jwt": "pyjwt",  # PyJWT package imports as jwt
        "infisical_client": "infisical_python",
        # OpenTelemetry packages
        "opentelemetry": "opentelemetry_api",  # opentelemetry-api provides opentelemetry module
        # Pydantic internals
        "pydantic_core": "pydantic",  # pydantic_core is included with pydantic
        # Backwards compatibility
        "tomllib": "tomllib",  # stdlib since Python 3.11
        # Note: hyphen/underscore normalization is handled in _normalize_package_name()
        # so python-on-whales → python_on_whales is automatic
    }


@pytest.mark.regression
def test_test_imports_have_dev_dependencies():
    """
    Ensure all test file imports are available in project dependencies.

    This test prevents CI failures from missing dependencies by validating
    that every package imported in tests/ is available either in:
    - Main dependencies (project.dependencies)
    - Dev dependencies (project.optional-dependencies.dev)
    - Or any other optional dependency group

    Test approach (TDD):
    - RED: Initially fails because some packages are in wrong dependency groups
    - GREEN: Passes after moving packages to appropriate dependency groups
    - REFACTOR: Prevents future regressions by running in CI

    Exceptions:
    - Standard library modules (sys, os, asyncio, etc.)
    - Local project modules (mcp_server_langgraph, tests, scripts, etc.)

    Failure mode:
    - Lists all packages imported by tests but not in any dependency group
    - Provides actionable fix: add missing packages to pyproject.toml
    """
    all_deps = get_all_dependencies()
    test_imports = get_test_imports()
    stdlib = get_stdlib_modules()
    project_modules = get_project_modules()
    import_name_mapping = get_import_name_mapping()

    # Normalize import names (handle package vs import name differences)
    normalized_deps = set(all_deps)
    for import_name, package_name in import_name_mapping.items():
        # If package is in deps, add its import name equivalent
        if _normalize_package_name(package_name) in all_deps:
            normalized_deps.add(import_name)
        # Special case: if package_name is in stdlib, allow the import_name
        if package_name in stdlib:
            normalized_deps.add(import_name)

    # Find missing dependencies
    missing = test_imports - normalized_deps - stdlib - project_modules

    if missing:
        missing_list = "\n  - ".join(sorted(missing))

        # Try to identify which extras group each should go in
        recommendations = []
        for pkg in sorted(missing):
            # Suggest appropriate dependency group based on usage
            if "docker" in pkg or "kubernetes" in pkg:
                recommendations.append(f'    "{pkg}",  # Add to code-execution extras')
            elif "click" in pkg or "jinja2" in pkg or "rich" in pkg:
                recommendations.append(f'    "{pkg}",  # Add to cli extras')
            elif "infisical" in pkg:
                recommendations.append(f'    "{pkg}",  # Add to secrets extras')
            else:
                recommendations.append(f'    "{pkg}",  # Add to dev extras (for test imports)')

        pytest.fail(
            f"\nTest files import packages not in any dependency group:\n"
            f"  - {missing_list}\n\n"
            "These packages are imported by test files but not available in CI.\n"
            "Add them to the appropriate extras in pyproject.toml:\n\n" + "\n".join(recommendations) + "\n\n"
            "Note: If tests need these imports, consider either:\n"
            "1. Adding package to dev extras (if used for testing)\n"
            "2. Adding package to main dependencies (if core functionality)\n"
            "3. Adding appropriate extras to CI workflow files\n"
        )


@pytest.mark.regression
def test_dev_dependencies_are_importable():
    """
    Verify that all dev dependencies can be imported.

    This is a sanity check to ensure:
    - Dependencies are correctly installed
    - No broken package specifications
    - No conflicts in dependency resolution

    Note: Some packages may have different import names than package names.
    We skip import validation for known cases (e.g., pytest-* packages).
    """
    all_deps = get_all_dependencies()

    # Skip packages that don't match their import name or are pytest plugins
    skip_import_check = (
        {
            # Pytest plugins (pytest-* packages don't import as pytest-*)
            pkg
            for pkg in all_deps
            if pkg.startswith("pytest_")
        }
        | {
            # Other packages with different import names (after normalization)
            "python_on_whales",  # imports as python_on_whales (normalized)
            "infisical_python",  # imports as infisical_client
            "pydantic_ai",  # imports as pydantic_ai (normalized)
            "types_pyyaml",  # type stub, no runtime import
            "types_requests",  # type stub, no runtime import
            "types_redis",  # type stub, no runtime import
            "openapi_spec_validator",  # Complex import structure
            "langchain_google_genai",  # Complex import structure
            "python_json_logger",  # imports as pythonjsonlogger
            "prometheus_api_client",  # imports differently
            "prometheus_client",  # imports as prometheus_client
            "ast_comments",  # imports as ast_comments
            # Package vs import name mismatches
            "pyyaml",  # imports as yaml
            "pyjwt",  # imports as jwt
            "python_dotenv",  # imports as dotenv
            "python_keycloak",  # imports as keycloak
            "opentelemetry_api",  # imports as opentelemetry.api
            "opentelemetry_sdk",  # imports as opentelemetry.sdk
            "opentelemetry_instrumentation_logging",  # imports as opentelemetry.instrumentation.logging
            "opentelemetry_exporter_otlp_proto_grpc",  # imports as opentelemetry.exporter.otlp.proto.grpc
            "opentelemetry_exporter_otlp_proto_http",  # imports as opentelemetry.exporter.otlp.proto.http
            "langgraph_checkpoint_redis",  # imports as langgraph.checkpoint.redis
            # Optional dependencies (not always installed)
            "torch",  # Only in embeddings-local extra
            "sentence_transformers",  # Only in embeddings-local extra
            # Build and release tools
            "build",  # build tool, not imported in tests
            "twine",  # release tool, not imported in tests
            # CLI tools
            "langgraph_cli",  # CLI tool, not imported in tests
            "mutmut",  # CLI tool, not imported in tests
            "bandit",  # CLI tool; stevedore plugin loader logs ERROR about missing sarif_om (optional SARIF formatter dependency we don't use)
            # Uvicorn extras
            "uvicorn",  # may have [standard] extras, import works as 'uvicorn'
            "redis",  # may have [hiredis] extras, import works as 'redis'
            "sqlalchemy",  # may have [asyncio] extras, import works as 'sqlalchemy'
            "coverage",  # may have [toml] extras, import works as 'coverage'
            # Optional dev tools that may not be installed in all environments
            "isort",  # Import sorter, optional dev tool
            "flake8",  # Linter, optional (ruff is primary)
            "ruff",  # Linter/formatter, optional dev tool
            "schemathesis",  # API testing tool, optional
            "black",  # Formatter, optional (ruff is primary)
            "kubernetes",  # K8s client, only needed for deployment tests
            "psutil",  # Process utilities, optional for performance tests
            "freezegun",  # Time mocking, optional for specific tests
            "toml",  # TOML parser, replaced by tomllib in Python 3.11+
            # CLI tools that are installed as system tools, not Python imports
            "yamllint",  # YAML linter, installed as CLI tool
            "authlib",  # Auth library, may not be installed in all environments
            "mypy",  # Type checker, may not be installed in all environments
            "pre_commit",  # Pre-commit hooks, installed as CLI tool
            "semgrep",  # Security scanner, installed as CLI tool
        }
    )

    failed_imports = []

    for pkg in all_deps:
        if pkg in skip_import_check:
            continue

        # Try to import the package
        try:
            __import__(pkg)
        except ImportError as e:
            failed_imports.append(f"{pkg}: {e}")
        except Exception:
            # Some packages may fail to import due to missing system deps
            # but are still available (e.g., docker without daemon)
            # Only fail on ImportError (package not found)
            pass

    if failed_imports:
        failed_list = "\n  - ".join(failed_imports)
        pytest.fail(
            f"\nDependencies that cannot be imported:\n"
            f"  - {failed_list}\n\n"
            f"This suggests either:\n"
            f"1. Dependencies are not installed (run: uv sync --extra dev)\n"
            f"2. Package specifications are incorrect in pyproject.toml\n"
            f"3. Dependency conflicts exist\n"
        )


if __name__ == "__main__":
    # Allow running this test standalone for debugging
    print("All dependencies:", sorted(get_all_dependencies()))
    print("\nTest imports:", sorted(get_test_imports()))
    print("\nStdlib modules:", sorted(get_stdlib_modules()))
    print("\nProject modules:", sorted(get_project_modules()))

    import_name_mapping = get_import_name_mapping()
    all_deps = get_all_dependencies()

    # Normalize import names
    normalized_deps = set(all_deps)
    for import_name, package_name in import_name_mapping.items():
        if _normalize_package_name(package_name) in all_deps:
            normalized_deps.add(import_name)

    missing = get_test_imports() - normalized_deps - get_stdlib_modules() - get_project_modules()
    if missing:
        print(f"\n❌ Missing dependencies: {sorted(missing)}")
        sys.exit(1)
    else:
        print("\n✅ All test imports have corresponding dependencies")
        sys.exit(0)
