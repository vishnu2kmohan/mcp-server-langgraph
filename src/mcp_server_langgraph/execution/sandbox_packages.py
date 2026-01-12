"""
Sandbox Package Configuration
=============================

Shared configuration for packages available in code execution environments.
This ensures parity between:
1. Docker/Kubernetes sandbox (server-side execution)
2. Pyodide (client-side browser execution)

Usage:
    from mcp_server_langgraph.execution.sandbox_packages import (
        SANDBOX_PACKAGES,
        get_allowed_imports,
        get_pip_packages,
    )

SECURITY NOTES
--------------
Network Packages (httpx, requests, aiohttp):
    These packages can make external HTTP requests. They only function when:
    - code_execution_network_mode = "allowlist" or "unrestricted"
    - Default is "none" (network disabled for security)

    IMPORTANT: Enabling network access allows sandbox code to:
    - Exfiltrate data to external servers
    - Access internal network resources
    - Make API calls with potential cost implications

    Only enable network access in trusted environments.

Database Package (sqlalchemy):
    Requires database connection strings with credentials.
    Code can access any database the connection string permits.

Docker-Only Packages:
    Packages marked with docker_only=True are not available in Pyodide browser.
    Code using these will work in Docker sandbox but fail in browser execution.
"""

from typing import TypedDict


class PackageSpec(TypedDict, total=False):
    """Specification for a sandbox package."""

    pip_name: str  # Name for pip install (may differ from import name)
    import_names: list[str]  # Python import names and aliases
    pyodide_name: str  # Name for Pyodide loadPackage (may differ)
    category: str  # Package category for organization
    description: str  # Brief description
    dependencies: list[str]  # Other packages this depends on
    docker_only: bool  # True if package is only available in Docker (not Pyodide)


# =============================================================================
# Core Package Configuration
# =============================================================================

SANDBOX_PACKAGES: dict[str, PackageSpec] = {
    # -------------------------------------------------------------------------
    # Data Science Core
    # -------------------------------------------------------------------------
    "numpy": {
        "pip_name": "numpy",
        "import_names": ["numpy", "np"],
        "pyodide_name": "numpy",
        "category": "data-science",
        "description": "Numerical computing arrays and operations",
        "dependencies": [],
    },
    "pandas": {
        "pip_name": "pandas",
        "import_names": ["pandas", "pd"],
        "pyodide_name": "pandas",
        "category": "data-science",
        "description": "Data manipulation and analysis",
        "dependencies": ["numpy"],
    },
    "scipy": {
        "pip_name": "scipy",
        "import_names": ["scipy"],
        "pyodide_name": "scipy",
        "category": "data-science",
        "description": "Scientific computing toolkit",
        "dependencies": ["numpy"],
    },
    # -------------------------------------------------------------------------
    # Machine Learning
    # -------------------------------------------------------------------------
    "scikit-learn": {
        "pip_name": "scikit-learn",
        "import_names": ["sklearn"],
        "pyodide_name": "scikit-learn",
        "category": "machine-learning",
        "description": "Machine learning algorithms",
        "dependencies": ["numpy", "scipy"],
    },
    "xgboost": {
        "pip_name": "xgboost",
        "import_names": ["xgboost", "xgb"],
        "pyodide_name": "xgboost",
        "category": "machine-learning",
        "description": "Gradient boosting (state-of-the-art for tabular data)",
        "dependencies": ["numpy", "scipy"],
    },
    "lightgbm": {
        "pip_name": "lightgbm",
        "import_names": ["lightgbm", "lgb"],
        "pyodide_name": "lightgbm",
        "category": "machine-learning",
        "description": "Fast gradient boosting (efficient for large datasets)",
        "dependencies": ["numpy", "scipy"],
    },
    # -------------------------------------------------------------------------
    # Visualization
    # -------------------------------------------------------------------------
    "matplotlib": {
        "pip_name": "matplotlib",
        "import_names": ["matplotlib", "matplotlib.pyplot", "plt"],
        "pyodide_name": "matplotlib",
        "category": "visualization",
        "description": "Plotting and visualization",
        "dependencies": ["numpy"],
    },
    "seaborn": {
        "pip_name": "seaborn",
        "import_names": ["seaborn", "sns"],
        "pyodide_name": "seaborn",
        "category": "visualization",
        "description": "Statistical data visualization",
        "dependencies": ["matplotlib", "pandas"],
    },
    "bokeh": {
        "pip_name": "bokeh",
        "import_names": ["bokeh", "bokeh.plotting"],
        "pyodide_name": "bokeh",
        "category": "visualization",
        "description": "Interactive web visualization (low-level control)",
        "dependencies": ["numpy"],
    },
    "altair": {
        "pip_name": "altair",
        "import_names": ["altair", "alt"],
        "pyodide_name": "altair",
        "category": "visualization",
        "description": "Declarative visualization (preferred for interactive plots)",
        "dependencies": ["pandas"],
    },
    # -------------------------------------------------------------------------
    # Math & Science
    # -------------------------------------------------------------------------
    "sympy": {
        "pip_name": "sympy",
        "import_names": ["sympy"],
        "pyodide_name": "sympy",
        "category": "math",
        "description": "Symbolic mathematics",
        "dependencies": [],
    },
    "networkx": {
        "pip_name": "networkx",
        "import_names": ["networkx", "nx"],
        "pyodide_name": "networkx",
        "category": "math",
        "description": "Graph and network analysis",
        "dependencies": [],
    },
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    "statsmodels": {
        "pip_name": "statsmodels",
        "import_names": ["statsmodels"],
        "pyodide_name": "statsmodels",
        "category": "statistics",
        "description": "Statistical modeling",
        "dependencies": ["numpy", "scipy", "pandas"],
    },
    # -------------------------------------------------------------------------
    # Image Processing
    # -------------------------------------------------------------------------
    "pillow": {
        "pip_name": "pillow",
        "import_names": ["PIL", "pillow"],
        "pyodide_name": "pillow",
        "category": "image-processing",
        "description": "Image processing library",
        "dependencies": [],
    },
    "scikit-image": {
        "pip_name": "scikit-image",
        "import_names": ["skimage"],
        "pyodide_name": "scikit-image",
        "category": "image-processing",
        "description": "Advanced image processing (segmentation, morphology, features)",
        "dependencies": ["numpy", "scipy"],
    },
    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------
    "regex": {
        "pip_name": "regex",
        "import_names": ["regex"],
        "pyodide_name": "regex",
        "category": "utilities",
        "description": "Advanced regular expressions",
        "dependencies": [],
    },
    "python-dateutil": {
        "pip_name": "python-dateutil",
        "import_names": ["dateutil"],
        "pyodide_name": "python-dateutil",
        "category": "utilities",
        "description": "Date/time utilities",
        "dependencies": [],
    },
    "pyyaml": {
        "pip_name": "pyyaml",
        "import_names": ["yaml"],
        "pyodide_name": "pyyaml",
        "category": "utilities",
        "description": "YAML parser",
        "dependencies": [],
    },
    "lxml": {
        "pip_name": "lxml",
        "import_names": ["lxml"],
        "pyodide_name": "lxml",
        "category": "utilities",
        "description": "Fast XML/HTML parsing with XPath",
        "dependencies": [],
    },
    # -------------------------------------------------------------------------
    # Scientific Data Formats
    # -------------------------------------------------------------------------
    "xarray": {
        "pip_name": "xarray",
        "import_names": ["xarray", "xr"],
        "pyodide_name": "xarray",
        "category": "scientific-data",
        "description": "N-dimensional labeled arrays (climate, geospatial)",
        "dependencies": ["numpy", "pandas"],
    },
    "h5py": {
        "pip_name": "h5py",
        "import_names": ["h5py"],
        "pyodide_name": "h5py",
        "category": "scientific-data",
        "description": "HDF5 file format for large datasets",
        "dependencies": ["numpy"],
    },
    # -------------------------------------------------------------------------
    # Network & HTTP
    # -------------------------------------------------------------------------
    "httpx": {
        "pip_name": "httpx",
        "import_names": ["httpx"],
        "pyodide_name": "httpx",
        "category": "network",
        "description": "Modern HTTP client (sync + async)",
        "dependencies": [],
    },
    "requests": {
        "pip_name": "requests",
        "import_names": ["requests"],
        "pyodide_name": "requests",
        "category": "network",
        "description": "HTTP client library",
        "dependencies": [],
    },
    "aiohttp": {
        "pip_name": "aiohttp",
        "import_names": ["aiohttp"],
        "pyodide_name": "aiohttp",
        "category": "network",
        "description": "Async HTTP client/server",
        "dependencies": [],
    },
    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    "sqlalchemy": {
        "pip_name": "sqlalchemy",
        "import_names": ["sqlalchemy"],
        "pyodide_name": "sqlalchemy",
        "category": "database",
        "description": "SQL toolkit and ORM",
        "dependencies": [],
    },
    # -------------------------------------------------------------------------
    # LLM Utilities
    # -------------------------------------------------------------------------
    "tiktoken": {
        "pip_name": "tiktoken",
        "import_names": ["tiktoken"],
        "pyodide_name": "tiktoken",
        "category": "llm",
        "description": "OpenAI tokenizer for token counting",
        "dependencies": [],
    },
    # -------------------------------------------------------------------------
    # High-Performance Data (Docker Only)
    # -------------------------------------------------------------------------
    "polars": {
        "pip_name": "polars",
        "import_names": ["polars", "pl"],
        "pyodide_name": "",  # Not available in Pyodide
        "category": "data-science",
        "description": "High-performance DataFrame (faster than pandas for large data)",
        "dependencies": [],
        "docker_only": True,
    },
    # -------------------------------------------------------------------------
    # Database Dialects (Docker Only)
    # These require native database drivers that can't run in WebAssembly.
    # Pyodide's SQLAlchemy is limited to SQLite via built-in sqlite3 module.
    # -------------------------------------------------------------------------
    "duckdb": {
        "pip_name": "duckdb",
        "import_names": ["duckdb"],
        "pyodide_name": "",  # Removed from Pyodide 0.28+ due to ABI issues
        "category": "database-dialect",
        "description": "Embedded analytics database (OLAP, columnar)",
        "dependencies": [],
        "docker_only": True,
    },
    "duckdb-engine": {
        "pip_name": "duckdb-engine",
        "import_names": ["duckdb_engine"],
        "pyodide_name": "",  # Requires duckdb which is Docker-only
        "category": "database-dialect",
        "description": "SQLAlchemy dialect for DuckDB",
        "dependencies": ["duckdb"],
        "docker_only": True,
    },
    "redshift-connector": {
        "pip_name": "redshift-connector",
        "import_names": ["redshift_connector"],
        "pyodide_name": "",  # Requires native C extensions
        "category": "database-dialect",
        "description": "Amazon Redshift database connector (direct driver, SQLAlchemy 2.0 compatible)",
        "dependencies": [],
        "docker_only": True,
    },
    "sqlalchemy-bigquery": {
        "pip_name": "sqlalchemy-bigquery",
        "import_names": ["sqlalchemy_bigquery"],
        "pyodide_name": "",  # Requires google-cloud SDK
        "category": "database-dialect",
        "description": "SQLAlchemy dialect for Google BigQuery",
        "dependencies": [],
        "docker_only": True,
    },
    "snowflake-sqlalchemy": {
        "pip_name": "snowflake-sqlalchemy",
        "import_names": ["snowflake", "snowflake.sqlalchemy"],
        "pyodide_name": "",  # Requires snowflake-connector (C crypto libs)
        "category": "database-dialect",
        "description": "SQLAlchemy dialect for Snowflake",
        "dependencies": [],
        "docker_only": True,
    },
    "sqlalchemy-cockroachdb": {
        "pip_name": "sqlalchemy-cockroachdb",
        "import_names": ["cockroachdb"],
        "pyodide_name": "",  # Requires psycopg2 (PostgreSQL wire protocol)
        "category": "database-dialect",
        "description": "SQLAlchemy dialect for CockroachDB",
        "dependencies": [],
        "docker_only": True,
    },
    # NOTE: ibm-db-sa removed - requires ibm-db which fails to build on ARM64 (aarch64)
    # The ibm-db package has a setup.py bug (undefined 'arch_' variable) on ARM architectures
}

# Standard library modules that are safe to import
SAFE_STDLIB_MODULES = [
    "json",
    "math",
    "datetime",
    "statistics",
    "collections",
    "itertools",
    "functools",
    "typing",
    "decimal",
    "fractions",
    "random",
    "string",
    "re",
    "textwrap",
    "unicodedata",
    "io",
    "base64",
    "hashlib",
    "hmac",
    "csv",
    "operator",
    "copy",
    "pprint",
    "enum",
    "dataclasses",
    "abc",
    "contextlib",
]


# =============================================================================
# Helper Functions
# =============================================================================


def get_allowed_imports() -> list[str]:
    """
    Get the list of allowed Python imports for code validation.

    Returns:
        List of import names (module and common aliases) that are whitelisted.
    """
    imports = list(SAFE_STDLIB_MODULES)

    for spec in SANDBOX_PACKAGES.values():
        imports.extend(spec["import_names"])

    return sorted(set(imports))


def get_pip_packages() -> list[str]:
    """
    Get the list of pip packages to install in Docker sandbox.

    Returns:
        List of pip package names.
    """
    return sorted(spec["pip_name"] for spec in SANDBOX_PACKAGES.values())


def get_pyodide_packages() -> dict[str, str]:
    """
    Get mapping of import names to Pyodide package names.

    Returns:
        Dict mapping Python import name to Pyodide package name.
    """
    mapping = {}
    for spec in SANDBOX_PACKAGES.values():
        pyodide_name = spec["pyodide_name"]
        for import_name in spec["import_names"]:
            mapping[import_name] = pyodide_name
    return mapping


def get_pyodide_lazy_packages() -> dict[str, list[str]]:
    """
    Get Pyodide packages with their dependencies for lazy loading.

    Note: Skips Docker-only packages (docker_only=True or empty pyodide_name).

    Returns:
        Dict mapping package name to list of packages to load (including deps).
    """
    result = {}
    for spec in SANDBOX_PACKAGES.values():
        # Skip Docker-only packages (not available in Pyodide)
        if spec.get("docker_only", False) or not spec["pyodide_name"]:
            continue
        pyodide_name = spec["pyodide_name"]
        deps = [
            SANDBOX_PACKAGES[d]["pyodide_name"]
            for d in spec.get("dependencies", [])
            if d in SANDBOX_PACKAGES and not SANDBOX_PACKAGES[d].get("docker_only", False)
        ]
        result[pyodide_name] = [pyodide_name] + deps
    return result


def get_core_packages() -> list[str]:
    """
    Get packages that should be loaded immediately (not lazy).

    These are packages used in nearly every data science session.

    Returns:
        List of Pyodide package names to load immediately.
    """
    return ["numpy", "matplotlib"]


def get_requirements_txt() -> str:
    """
    Generate requirements.txt content for Docker sandbox.

    Returns:
        String content for requirements.txt file.
    """
    lines = [
        "# Auto-generated from sandbox_packages.py",
        "# These packages match the Pyodide browser environment",
        "#",
        "# Categories:",
    ]

    # Group by category
    by_category: dict[str, list[str]] = {}
    for spec in SANDBOX_PACKAGES.values():
        cat = spec.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(f"{spec['pip_name']}  # {spec.get('description', '')}")

    for category in sorted(by_category.keys()):
        lines.append(f"\n# {category.replace('-', ' ').title()}")
        lines.extend(sorted(by_category[category]))

    return "\n".join(lines) + "\n"
