"""
Tests for Sandbox Package Configuration.

These tests verify the shared package configuration that ensures parity between
Docker sandbox and Pyodide browser environments.

TDD: Written FIRST to define expected behavior.
"""

import gc
from pathlib import Path

import pytest

from mcp_server_langgraph.execution.sandbox_packages import (
    SAFE_STDLIB_MODULES,
    SANDBOX_PACKAGES,
    get_allowed_imports,
    get_core_packages,
    get_pip_packages,
    get_pyodide_lazy_packages,
    get_pyodide_packages,
    get_requirements_txt,
)

pytestmark = [pytest.mark.unit, pytest.mark.execution]


@pytest.mark.xdist_group(name="sandbox_packages")
class TestSandboxPackagesConfiguration:
    """Tests for the SANDBOX_PACKAGES configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_packages_have_required_fields(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: Each package has required fields (pip_name, import_names, pyodide_name)
        """
        required_fields = ["pip_name", "import_names", "pyodide_name"]

        for pkg_name, spec in SANDBOX_PACKAGES.items():
            for field in required_fields:
                assert field in spec, f"Package '{pkg_name}' missing required field '{field}'"

    def test_import_names_are_lists(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: import_names field is a list with at least one entry
        """
        for pkg_name, spec in SANDBOX_PACKAGES.items():
            assert isinstance(spec["import_names"], list), f"Package '{pkg_name}' import_names should be a list"
            assert len(spec["import_names"]) >= 1, f"Package '{pkg_name}' should have at least one import name"

    def test_dependencies_reference_existing_packages(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES with dependencies
        THEN: All dependencies reference packages that exist in SANDBOX_PACKAGES
        """
        for pkg_name, spec in SANDBOX_PACKAGES.items():
            for dep in spec.get("dependencies", []):
                assert dep in SANDBOX_PACKAGES, (
                    f"Package '{pkg_name}' has dependency '{dep}' which doesn't exist in SANDBOX_PACKAGES"
                )

    def test_core_data_science_packages_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: Core data science packages are present
        """
        expected_packages = [
            "numpy",
            "pandas",
            "scipy",
            "matplotlib",
            "scikit-learn",
        ]
        for pkg in expected_packages:
            assert pkg in SANDBOX_PACKAGES, f"Expected core package '{pkg}' not in SANDBOX_PACKAGES"

    def test_categories_are_valid(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES with categories
        THEN: All categories are from a known set
        """
        valid_categories = {
            "data-science",
            "machine-learning",
            "visualization",
            "math",
            "statistics",
            "image-processing",
            "utilities",
            "scientific-data",
            "network",
            "database",
            "database-dialect",
            "llm",
        }
        for pkg_name, spec in SANDBOX_PACKAGES.items():
            category = spec.get("category")
            if category:
                assert category in valid_categories, f"Package '{pkg_name}' has unknown category '{category}'"


@pytest.mark.xdist_group(name="sandbox_packages")
class TestSafeStdlibModules:
    """Tests for safe standard library module list."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_safe_stdlib_includes_common_modules(self) -> None:
        """
        GIVEN: SAFE_STDLIB_MODULES list
        THEN: Common safe modules are included
        """
        expected = ["json", "math", "datetime", "re", "collections", "itertools"]
        for mod in expected:
            assert mod in SAFE_STDLIB_MODULES, f"Expected safe module '{mod}' not in SAFE_STDLIB_MODULES"

    def test_safe_stdlib_excludes_dangerous_modules(self) -> None:
        """
        GIVEN: SAFE_STDLIB_MODULES list
        THEN: Dangerous modules are NOT included
        """
        dangerous = ["os", "sys", "subprocess", "socket", "pickle", "ctypes"]
        for mod in dangerous:
            assert mod not in SAFE_STDLIB_MODULES, f"Dangerous module '{mod}' should NOT be in SAFE_STDLIB_MODULES"


@pytest.mark.xdist_group(name="sandbox_packages")
class TestGetAllowedImports:
    """Tests for get_allowed_imports function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_includes_stdlib_modules(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: It includes safe stdlib modules
        """
        allowed = get_allowed_imports()
        assert "json" in allowed
        assert "math" in allowed
        assert "datetime" in allowed

    def test_includes_package_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: It includes data science package imports
        """
        allowed = get_allowed_imports()
        assert "numpy" in allowed
        assert "pandas" in allowed
        assert "matplotlib" in allowed
        assert "sklearn" in allowed

    def test_includes_aliases_for_common_packages(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: It includes common import aliases
        """
        allowed = get_allowed_imports()
        assert "np" in allowed  # numpy alias
        assert "pd" in allowed  # pandas alias
        assert "plt" in allowed  # matplotlib.pyplot alias

    def test_returns_sorted_unique_list(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: It returns sorted list with no duplicates
        """
        allowed = get_allowed_imports()
        assert allowed == sorted(set(allowed))


@pytest.mark.xdist_group(name="sandbox_packages")
class TestGetPipPackages:
    """Tests for get_pip_packages function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_pip_names(self) -> None:
        """
        GIVEN: get_pip_packages() result
        THEN: It returns pip package names
        """
        packages = get_pip_packages()
        assert "numpy" in packages
        assert "pandas" in packages
        assert "scikit-learn" in packages  # pip name differs from import

    def test_returns_sorted_list(self) -> None:
        """
        GIVEN: get_pip_packages() result
        THEN: It returns sorted list
        """
        packages = get_pip_packages()
        assert packages == sorted(packages)


@pytest.mark.xdist_group(name="sandbox_packages")
class TestGetPyodidePackages:
    """Tests for get_pyodide_packages function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_maps_import_to_pyodide_name(self) -> None:
        """
        GIVEN: get_pyodide_packages() result
        THEN: It maps import names to Pyodide package names
        """
        mapping = get_pyodide_packages()

        assert mapping["numpy"] == "numpy"
        assert mapping["np"] == "numpy"
        assert mapping["pandas"] == "pandas"
        assert mapping["pd"] == "pandas"
        assert mapping["sklearn"] == "scikit-learn"
        assert mapping["PIL"] == "pillow"

    def test_includes_all_aliases(self) -> None:
        """
        GIVEN: get_pyodide_packages() result
        THEN: It includes all import aliases
        """
        mapping = get_pyodide_packages()

        # Check that all import_names from SANDBOX_PACKAGES are present
        for spec in SANDBOX_PACKAGES.values():
            for import_name in spec["import_names"]:
                assert import_name in mapping, f"Import name '{import_name}' not in Pyodide mapping"


@pytest.mark.xdist_group(name="sandbox_packages")
class TestGetCorePackages:
    """Tests for get_core_packages function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_includes_numpy_and_matplotlib(self) -> None:
        """
        GIVEN: get_core_packages() result
        THEN: It includes numpy and matplotlib
        """
        core = get_core_packages()
        assert "numpy" in core
        assert "matplotlib" in core

    def test_is_minimal_set(self) -> None:
        """
        GIVEN: get_core_packages() result
        THEN: It's a small set (avoid slow startup)
        """
        core = get_core_packages()
        assert len(core) <= 3, "Core packages should be minimal to avoid slow startup"


@pytest.mark.xdist_group(name="sandbox_packages")
class TestGetPyodideLazyPackages:
    """Tests for get_pyodide_lazy_packages function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_includes_dependencies_for_packages(self) -> None:
        """
        GIVEN: get_pyodide_lazy_packages() result
        THEN: Package entries include their dependencies
        """
        lazy = get_pyodide_lazy_packages()

        # scikit-learn depends on numpy, scipy
        sklearn_deps = lazy.get("scikit-learn", [])
        assert "scikit-learn" in sklearn_deps
        assert "numpy" in sklearn_deps
        assert "scipy" in sklearn_deps

    def test_package_includes_itself(self) -> None:
        """
        GIVEN: get_pyodide_lazy_packages() result
        THEN: Each package list includes the package itself
        """
        lazy = get_pyodide_lazy_packages()

        for pkg_name, deps in lazy.items():
            assert pkg_name in deps, f"Package '{pkg_name}' should include itself in deps"


@pytest.mark.xdist_group(name="sandbox_packages")
class TestInteractiveVisualization:
    """Tests for interactive visualization packages (Bokeh)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bokeh_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: Bokeh is present for interactive visualization
        """
        assert "bokeh" in SANDBOX_PACKAGES, "Bokeh should be in SANDBOX_PACKAGES"

    def test_bokeh_has_correct_import_names(self) -> None:
        """
        GIVEN: Bokeh package specification
        THEN: It has bokeh and bkh as import names
        """
        bokeh = SANDBOX_PACKAGES.get("bokeh", {})
        assert "bokeh" in bokeh.get("import_names", [])
        assert "bokeh.plotting" in bokeh.get("import_names", [])

    def test_bokeh_category_is_visualization(self) -> None:
        """
        GIVEN: Bokeh package specification
        THEN: It's categorized as visualization
        """
        bokeh = SANDBOX_PACKAGES.get("bokeh", {})
        assert bokeh.get("category") == "visualization"

    def test_bokeh_is_in_allowed_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: bokeh and bokeh.plotting are allowed
        """
        allowed = get_allowed_imports()
        assert "bokeh" in allowed
        assert "bokeh.plotting" in allowed

    def test_bokeh_maps_to_pyodide_package(self) -> None:
        """
        GIVEN: get_pyodide_packages() result
        THEN: bokeh imports map to bokeh Pyodide package
        """
        mapping = get_pyodide_packages()
        assert mapping.get("bokeh") == "bokeh"
        assert mapping.get("bokeh.plotting") == "bokeh"


@pytest.mark.xdist_group(name="sandbox_packages")
class TestGradientBoostingPackages:
    """Tests for gradient boosting ML packages (XGBoost, LightGBM)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_xgboost_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: XGBoost is present for gradient boosting
        """
        assert "xgboost" in SANDBOX_PACKAGES

    def test_xgboost_has_correct_import_names(self) -> None:
        """
        GIVEN: XGBoost package specification
        THEN: It has xgboost and xgb as import names
        """
        xgb = SANDBOX_PACKAGES.get("xgboost", {})
        assert "xgboost" in xgb.get("import_names", [])
        assert "xgb" in xgb.get("import_names", [])

    def test_lightgbm_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: LightGBM is present for gradient boosting
        """
        assert "lightgbm" in SANDBOX_PACKAGES

    def test_lightgbm_has_correct_import_names(self) -> None:
        """
        GIVEN: LightGBM package specification
        THEN: It has lightgbm and lgb as import names
        """
        lgb = SANDBOX_PACKAGES.get("lightgbm", {})
        assert "lightgbm" in lgb.get("import_names", [])
        assert "lgb" in lgb.get("import_names", [])

    def test_ml_packages_in_allowed_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: ML package aliases are allowed
        """
        allowed = get_allowed_imports()
        assert "xgboost" in allowed
        assert "xgb" in allowed
        assert "lightgbm" in allowed
        assert "lgb" in allowed


@pytest.mark.xdist_group(name="sandbox_packages")
class TestDeclarativeVisualization:
    """Tests for declarative visualization packages (Altair)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_altair_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: Altair is present for declarative visualization
        """
        assert "altair" in SANDBOX_PACKAGES

    def test_altair_has_correct_import_names(self) -> None:
        """
        GIVEN: Altair package specification
        THEN: It has altair and alt as import names
        """
        alt = SANDBOX_PACKAGES.get("altair", {})
        assert "altair" in alt.get("import_names", [])
        assert "alt" in alt.get("import_names", [])

    def test_altair_is_in_allowed_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: altair and alt are allowed
        """
        allowed = get_allowed_imports()
        assert "altair" in allowed
        assert "alt" in allowed


@pytest.mark.xdist_group(name="sandbox_packages")
class TestAdvancedImageProcessing:
    """Tests for advanced image processing packages (scikit-image)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scikit_image_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: scikit-image is present
        """
        assert "scikit-image" in SANDBOX_PACKAGES

    def test_scikit_image_has_correct_import_names(self) -> None:
        """
        GIVEN: scikit-image package specification
        THEN: It has skimage as import name
        """
        skimage = SANDBOX_PACKAGES.get("scikit-image", {})
        assert "skimage" in skimage.get("import_names", [])

    def test_skimage_is_in_allowed_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: skimage is allowed
        """
        allowed = get_allowed_imports()
        assert "skimage" in allowed


@pytest.mark.xdist_group(name="sandbox_packages")
class TestScientificDataPackages:
    """Tests for scientific data packages (xarray, h5py, lxml)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_xarray_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: xarray is present for N-dimensional data
        """
        assert "xarray" in SANDBOX_PACKAGES

    def test_xarray_has_correct_import_names(self) -> None:
        """
        GIVEN: xarray package specification
        THEN: It has xarray and xr as import names
        """
        xr = SANDBOX_PACKAGES.get("xarray", {})
        assert "xarray" in xr.get("import_names", [])
        assert "xr" in xr.get("import_names", [])

    def test_h5py_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: h5py is present for HDF5 files
        """
        assert "h5py" in SANDBOX_PACKAGES

    def test_lxml_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: lxml is present for XML/HTML parsing
        """
        assert "lxml" in SANDBOX_PACKAGES


@pytest.mark.xdist_group(name="sandbox_packages")
class TestLLMUtilities:
    """Tests for LLM utility packages (tiktoken)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tiktoken_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: tiktoken is present for token counting
        """
        assert "tiktoken" in SANDBOX_PACKAGES

    def test_tiktoken_has_correct_import_name(self) -> None:
        """
        GIVEN: tiktoken package specification
        THEN: It has tiktoken as import name
        """
        tiktoken = SANDBOX_PACKAGES.get("tiktoken", {})
        assert "tiktoken" in tiktoken.get("import_names", [])

    def test_tiktoken_is_in_allowed_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: tiktoken is allowed
        """
        allowed = get_allowed_imports()
        assert "tiktoken" in allowed


@pytest.mark.xdist_group(name="sandbox_packages")
class TestDockerOnlyPackages:
    """Tests for packages only available in Docker (not Pyodide)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_polars_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: polars is present for high-performance DataFrames
        """
        assert "polars" in SANDBOX_PACKAGES

    def test_polars_marked_docker_only(self) -> None:
        """
        GIVEN: polars package specification
        THEN: It's marked as Docker-only (not available in Pyodide)
        """
        polars = SANDBOX_PACKAGES.get("polars", {})
        assert polars.get("docker_only") is True

    def test_polars_has_correct_import_names(self) -> None:
        """
        GIVEN: polars package specification
        THEN: It has polars and pl as import names
        """
        polars = SANDBOX_PACKAGES.get("polars", {})
        assert "polars" in polars.get("import_names", [])
        assert "pl" in polars.get("import_names", [])


@pytest.mark.xdist_group(name="sandbox_packages")
class TestNetworkAndDatabasePackages:
    """Tests for network and database packages (httpx, requests, aiohttp, sqlalchemy)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_httpx_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: httpx is present for HTTP client
        """
        assert "httpx" in SANDBOX_PACKAGES

    def test_requests_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: requests is present for HTTP client
        """
        assert "requests" in SANDBOX_PACKAGES

    def test_aiohttp_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: aiohttp is present for async HTTP
        """
        assert "aiohttp" in SANDBOX_PACKAGES

    def test_sqlalchemy_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: sqlalchemy is present for database access
        """
        assert "sqlalchemy" in SANDBOX_PACKAGES

    def test_network_packages_in_allowed_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: Network packages are allowed
        """
        allowed = get_allowed_imports()
        assert "httpx" in allowed
        assert "requests" in allowed
        assert "aiohttp" in allowed
        assert "sqlalchemy" in allowed


@pytest.mark.xdist_group(name="sandbox_packages")
class TestGetRequirementsTxt:
    """Tests for get_requirements_txt function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generates_valid_requirements_format(self) -> None:
        """
        GIVEN: get_requirements_txt() result
        THEN: It generates valid pip requirements format
        """
        content = get_requirements_txt()

        # Should have package lines
        lines = content.strip().split("\n")
        package_lines = [line for line in lines if line and not line.startswith("#")]

        assert len(package_lines) > 0

        # Each package line should be a valid pip package name
        for line in package_lines:
            # Remove comments
            pkg_part = line.split("#")[0].strip()
            if pkg_part:
                assert " " not in pkg_part or "  #" in line, f"Invalid package line: {line}"


@pytest.mark.xdist_group(name="sandbox_packages")
class TestPyodideParity:
    """
    Tests ensuring parity between Python config and TypeScript Pyodide config.

    These tests verify that the frontend pyodidePackages.ts matches the backend
    sandbox_packages.py configuration.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_pyodide_import_mapping_matches(self) -> None:
        """
        GIVEN: Backend SANDBOX_PACKAGES and frontend pyodidePackages.ts
        THEN: Import-to-package mappings should match
        """
        # Get backend mapping
        backend_mapping = get_pyodide_packages()

        # Read frontend TypeScript file and extract mapping
        frontend_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "mcp_server_langgraph"
            / "studio"
            / "frontend"
            / "src"
            / "canvas"
            / "pyodidePackages.ts"
        )

        if not frontend_path.exists():
            pytest.skip(f"Frontend file not found at {frontend_path}")

        content = frontend_path.read_text()

        # Verify key mappings are present in frontend
        key_mappings = [
            ("numpy", "numpy"),
            ("np", "numpy"),
            ("pandas", "pandas"),
            ("pd", "pandas"),
            ("sklearn", "scikit-learn"),
            ("PIL", "pillow"),
            ("matplotlib", "matplotlib"),
            ("scipy", "scipy"),
        ]

        for import_name, expected_pkg in key_mappings:
            # Check backend
            assert backend_mapping.get(import_name) == expected_pkg, (
                f"Backend mapping for '{import_name}' should be '{expected_pkg}'"
            )

            # Check frontend contains this mapping
            # TypeScript allows unquoted keys like `np:` or quoted `"np":`
            import_present = (
                f'"{import_name}"' in content
                or f"'{import_name}'" in content
                or f"{import_name}:" in content  # TypeScript unquoted key
            )
            assert import_present, f"Frontend should contain import name '{import_name}'"
            pkg_present = f'"{expected_pkg}"' in content or f"'{expected_pkg}'" in content
            assert pkg_present, f"Frontend should contain package name '{expected_pkg}'"

    def test_core_packages_match(self) -> None:
        """
        GIVEN: Backend get_core_packages() and frontend PYODIDE_CORE_PACKAGES
        THEN: Core package lists should match
        """
        backend_core = get_core_packages()

        frontend_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "mcp_server_langgraph"
            / "studio"
            / "frontend"
            / "src"
            / "canvas"
            / "pyodidePackages.ts"
        )

        if not frontend_path.exists():
            pytest.skip(f"Frontend file not found at {frontend_path}")

        content = frontend_path.read_text()

        # Check that core packages are in frontend
        for pkg in backend_core:
            # PYODIDE_CORE_PACKAGES should contain these
            assert "PYODIDE_CORE_PACKAGES = [" in content, "Frontend should have PYODIDE_CORE_PACKAGES constant"
            assert f'"{pkg}"' in content, f"Frontend PYODIDE_CORE_PACKAGES should contain '{pkg}'"

    def test_lazy_packages_match(self) -> None:
        """
        GIVEN: Backend get_pyodide_lazy_packages() and frontend PYODIDE_LAZY_PACKAGES
        THEN: Lazy package lists should have same packages
        """
        backend_lazy = get_pyodide_lazy_packages()

        frontend_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "mcp_server_langgraph"
            / "studio"
            / "frontend"
            / "src"
            / "canvas"
            / "pyodidePackages.ts"
        )

        if not frontend_path.exists():
            pytest.skip(f"Frontend file not found at {frontend_path}")

        content = frontend_path.read_text()

        # Check that lazy packages are in frontend
        for pkg_name in backend_lazy.keys():
            assert f'"{pkg_name}"' in content or f"'{pkg_name}'" in content, (
                f"Frontend PYODIDE_LAZY_PACKAGES should contain '{pkg_name}'"
            )


@pytest.mark.xdist_group(name="sandbox_packages")
class TestSQLAlchemyDatabaseDialects:
    """Tests for SQLAlchemy database dialect packages (Docker-only).

    These packages provide SQLAlchemy dialects for cloud data warehouses
    and enterprise databases. They require native drivers and network access,
    so they are only available in the Docker sandbox (not Pyodide browser).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_duckdb_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: duckdb is present for embedded analytics
        """
        assert "duckdb" in SANDBOX_PACKAGES

    def test_duckdb_marked_docker_only(self) -> None:
        """
        GIVEN: duckdb package specification
        THEN: It's marked as Docker-only (not available in Pyodide 0.29+)
        """
        duckdb = SANDBOX_PACKAGES.get("duckdb", {})
        assert duckdb.get("docker_only") is True

    def test_duckdb_engine_package_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: duckdb-engine is present for SQLAlchemy integration
        """
        assert "duckdb-engine" in SANDBOX_PACKAGES

    def test_duckdb_engine_marked_docker_only(self) -> None:
        """
        GIVEN: duckdb-engine package specification
        THEN: It's marked as Docker-only
        """
        duckdb_engine = SANDBOX_PACKAGES.get("duckdb-engine", {})
        assert duckdb_engine.get("docker_only") is True

    def test_redshift_connector_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: redshift-connector is present for Amazon Redshift
        """
        assert "redshift-connector" in SANDBOX_PACKAGES

    def test_redshift_connector_marked_docker_only(self) -> None:
        """
        GIVEN: redshift-connector package specification
        THEN: It's marked as Docker-only
        """
        redshift = SANDBOX_PACKAGES.get("redshift-connector", {})
        assert redshift.get("docker_only") is True

    def test_bigquery_dialect_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: sqlalchemy-bigquery is present for Google BigQuery
        """
        assert "sqlalchemy-bigquery" in SANDBOX_PACKAGES

    def test_bigquery_dialect_marked_docker_only(self) -> None:
        """
        GIVEN: sqlalchemy-bigquery package specification
        THEN: It's marked as Docker-only
        """
        bigquery = SANDBOX_PACKAGES.get("sqlalchemy-bigquery", {})
        assert bigquery.get("docker_only") is True

    def test_snowflake_dialect_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: snowflake-sqlalchemy is present for Snowflake
        """
        assert "snowflake-sqlalchemy" in SANDBOX_PACKAGES

    def test_snowflake_dialect_marked_docker_only(self) -> None:
        """
        GIVEN: snowflake-sqlalchemy package specification
        THEN: It's marked as Docker-only
        """
        snowflake = SANDBOX_PACKAGES.get("snowflake-sqlalchemy", {})
        assert snowflake.get("docker_only") is True

    def test_cockroachdb_dialect_present(self) -> None:
        """
        GIVEN: SANDBOX_PACKAGES configuration
        THEN: sqlalchemy-cockroachdb is present for CockroachDB
        """
        assert "sqlalchemy-cockroachdb" in SANDBOX_PACKAGES

    def test_cockroachdb_dialect_marked_docker_only(self) -> None:
        """
        GIVEN: sqlalchemy-cockroachdb package specification
        THEN: It's marked as Docker-only
        """
        cockroachdb = SANDBOX_PACKAGES.get("sqlalchemy-cockroachdb", {})
        assert cockroachdb.get("docker_only") is True

    # NOTE: ibm-db-sa tests removed - ibm-db fails to build on ARM64 (aarch64)
    # The ibm-db package has a setup.py bug (undefined 'arch_' variable) on ARM architectures

    def test_database_dialects_in_allowed_imports(self) -> None:
        """
        GIVEN: get_allowed_imports() result
        THEN: Database dialect imports are allowed
        """
        allowed = get_allowed_imports()
        assert "duckdb" in allowed
        assert "duckdb_engine" in allowed
        assert "redshift_connector" in allowed
        assert "sqlalchemy_bigquery" in allowed
        assert "snowflake" in allowed
        assert "cockroachdb" in allowed
        # NOTE: ibm_db_sa removed - ibm-db fails to build on ARM64

    def test_database_dialects_have_correct_category(self) -> None:
        """
        GIVEN: Database dialect packages
        THEN: They have 'database-dialect' category
        """
        dialect_packages = [
            "duckdb",
            "duckdb-engine",
            "redshift-connector",
            "sqlalchemy-bigquery",
            "snowflake-sqlalchemy",
            "sqlalchemy-cockroachdb",
            # NOTE: ibm-db-sa removed - ibm-db fails to build on ARM64
        ]
        for pkg_name in dialect_packages:
            pkg = SANDBOX_PACKAGES.get(pkg_name, {})
            assert pkg.get("category") == "database-dialect", f"Package '{pkg_name}' should have 'database-dialect' category"
