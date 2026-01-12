/**
 * Pyodide Package Configuration and Lazy Loading Utilities
 *
 * This module handles detection of Python imports from source code and
 * mapping them to Pyodide packages for lazy loading.
 *
 * IMPORTANT: Package Parity
 * -------------------------
 * These packages MUST match the Docker sandbox environment to ensure code
 * runs the same way in both browser (Pyodide) and server (Docker) runtimes.
 *
 * Source of truth: src/mcp_server_langgraph/execution/sandbox_packages.py
 *
 * Key features:
 * - Import detection via regex parsing
 * - Package name mapping (Python module -> Pyodide package)
 * - Dependency resolution for packages that require other packages
 * - Session-based caching to avoid reloading packages
 */

// =============================================================================
// Package Configuration (mirrors sandbox_packages.py)
// =============================================================================

/**
 * Maps Python import names to Pyodide package names.
 * Most packages use the same name, but some differ (e.g., PIL -> pillow).
 *
 * Keep in sync with: sandbox_packages.py SANDBOX_PACKAGES
 */
export const PYODIDE_IMPORT_TO_PACKAGE: Record<string, string> = {
  // Data Science Core
  numpy: "numpy",
  np: "numpy",
  pandas: "pandas",
  pd: "pandas",
  scipy: "scipy",
  // Machine Learning
  sklearn: "scikit-learn",
  xgboost: "xgboost",
  xgb: "xgboost",
  lightgbm: "lightgbm",
  lgb: "lightgbm",
  // Visualization
  matplotlib: "matplotlib",
  plt: "matplotlib",
  seaborn: "seaborn",
  sns: "seaborn",
  bokeh: "bokeh",
  "bokeh.plotting": "bokeh",
  // Declarative Visualization (preferred for interactive plots)
  altair: "altair",
  alt: "altair",
  // Math & Science
  sympy: "sympy",
  networkx: "networkx",
  nx: "networkx",
  // Image Processing
  PIL: "pillow",
  pillow: "pillow",
  skimage: "scikit-image",
  // Scientific Data
  xarray: "xarray",
  xr: "xarray",
  h5py: "h5py",
  // Utilities
  regex: "regex",
  dateutil: "python-dateutil",
  yaml: "pyyaml",
  lxml: "lxml",
  // Statistics
  statsmodels: "statsmodels",
  // Network & HTTP
  httpx: "httpx",
  requests: "requests",
  aiohttp: "aiohttp",
  // Database
  sqlalchemy: "sqlalchemy",
  // LLM Utilities
  tiktoken: "tiktoken",
};

/**
 * Core packages that are always loaded (fast, universally needed).
 * These are loaded immediately when Pyodide starts.
 *
 * Keep in sync with: sandbox_packages.py get_core_packages()
 */
export const PYODIDE_CORE_PACKAGES = ["numpy", "matplotlib"];

/**
 * All available lazy-loadable packages with their dependencies.
 * Loaded on-demand when detected in user code.
 *
 * Keep in sync with: sandbox_packages.py get_pyodide_lazy_packages()
 */
export const PYODIDE_LAZY_PACKAGES: Record<string, string[]> = {
  // Data Science Core
  pandas: ["pandas", "numpy"],
  scipy: ["scipy", "numpy"],
  // Machine Learning
  "scikit-learn": ["scikit-learn", "numpy", "scipy"],
  xgboost: ["xgboost", "numpy", "scipy"],
  lightgbm: ["lightgbm", "numpy", "scipy"],
  // Visualization
  seaborn: ["seaborn", "matplotlib", "pandas"],
  bokeh: ["bokeh", "numpy"],
  // Declarative Visualization (preferred for interactive plots)
  altair: ["altair", "pandas"],
  // Math & Science
  sympy: ["sympy"],
  networkx: ["networkx"],
  // Statistics
  statsmodels: ["statsmodels", "numpy", "scipy", "pandas"],
  // Image Processing
  pillow: ["pillow"],
  "scikit-image": ["scikit-image", "numpy", "scipy"],
  // Scientific Data
  xarray: ["xarray", "numpy", "pandas"],
  h5py: ["h5py", "numpy"],
  // Utilities
  regex: ["regex"],
  "python-dateutil": ["python-dateutil"],
  pyyaml: ["pyyaml"],
  lxml: ["lxml"],
  // Network & HTTP
  httpx: ["httpx"],
  requests: ["requests"],
  aiohttp: ["aiohttp"],
  // Database
  sqlalchemy: ["sqlalchemy"],
  // LLM Utilities
  tiktoken: ["tiktoken"],
};

// =============================================================================
// Package State Management
// =============================================================================

/**
 * Track which packages have been loaded in the current session.
 * Persists across multiple code executions within the same page load.
 */
const loadedPackagesSet = new Set<string>(PYODIDE_CORE_PACKAGES);

/**
 * Check if a package has been loaded.
 */
export function isPackageLoaded(packageName: string): boolean {
  return loadedPackagesSet.has(packageName);
}

/**
 * Mark packages as loaded after successful installation.
 */
export function markPackagesLoaded(packages: string[]): void {
  packages.forEach((pkg) => loadedPackagesSet.add(pkg));
}

/**
 * Get the set of currently loaded packages.
 */
export function getLoadedPackages(): Set<string> {
  return new Set(loadedPackagesSet);
}

/**
 * Reset loaded packages (for testing).
 */
export function resetLoadedPackages(): void {
  loadedPackagesSet.clear();
  PYODIDE_CORE_PACKAGES.forEach((pkg) => loadedPackagesSet.add(pkg));
}

// =============================================================================
// Import Detection
// =============================================================================

/**
 * Detect Python imports from source code.
 * Handles:
 * - import X
 * - import X as Y
 * - import X, Y, Z
 * - from X import ...
 * - from X.submodule import ...
 *
 * @param code Python source code
 * @returns Set of top-level module names detected
 */
export function detectPythonImports(code: string): Set<string> {
  const imports = new Set<string>();

  // Pattern 1: import X, import X as Y, import X, Y, Z
  // Matches: "import numpy", "import numpy as np", "import os, sys, re"
  const importPattern =
    /^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*)*)/gm;
  let match;
  while ((match = importPattern.exec(code)) !== null) {
    const modules = match[1]
      .split(",")
      .map((m) => m.trim().split(/\s+as\s+/)[0]);
    modules.forEach((m) => imports.add(m));
  }

  // Pattern 2: from X import ... or from X.submodule import ...
  // Matches: "from numpy import array", "from sklearn.model_selection import train_test_split"
  const fromPattern =
    /^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\s+import/gm;
  while ((match = fromPattern.exec(code)) !== null) {
    imports.add(match[1]);
  }

  return imports;
}

// =============================================================================
// Package Resolution
// =============================================================================

/**
 * Determine which Pyodide packages need to be loaded for the given code.
 * Returns only packages that haven't been loaded yet.
 *
 * @param code Python source code
 * @returns Array of package names to load
 */
export function getRequiredPackages(code: string): string[] {
  const detectedImports = detectPythonImports(code);
  const packagesToLoad = new Set<string>();

  for (const importName of detectedImports) {
    const pyodidePackage = PYODIDE_IMPORT_TO_PACKAGE[importName];
    if (pyodidePackage && !loadedPackagesSet.has(pyodidePackage)) {
      // Add the package and its dependencies
      const deps = PYODIDE_LAZY_PACKAGES[pyodidePackage];
      if (deps) {
        deps.forEach((dep) => {
          if (!loadedPackagesSet.has(dep)) {
            packagesToLoad.add(dep);
          }
        });
      } else {
        packagesToLoad.add(pyodidePackage);
      }
    }
  }

  return Array.from(packagesToLoad);
}
