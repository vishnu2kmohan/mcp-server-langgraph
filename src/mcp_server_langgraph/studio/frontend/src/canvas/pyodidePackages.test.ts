/**
 * Pyodide Package Utilities Tests
 *
 * Tests for Python import detection and Pyodide package resolution.
 * These utilities enable lazy loading of packages based on user code.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  detectPythonImports,
  getRequiredPackages,
  markPackagesLoaded,
  isPackageLoaded,
  resetLoadedPackages,
  getLoadedPackages,
  PYODIDE_IMPORT_TO_PACKAGE,
  PYODIDE_CORE_PACKAGES,
  PYODIDE_LAZY_PACKAGES,
} from "./pyodidePackages";

describe("pyodidePackages", () => {
  beforeEach(() => {
    // Reset package state before each test
    resetLoadedPackages();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("detectPythonImports", () => {
    it("should detect simple import statements", () => {
      const code = `import numpy`;
      const imports = detectPythonImports(code);
      expect(imports.has("numpy")).toBe(true);
    });

    it("should detect import with alias", () => {
      const code = `import numpy as np`;
      const imports = detectPythonImports(code);
      expect(imports.has("numpy")).toBe(true);
      expect(imports.has("np")).toBe(false); // Should only detect module name
    });

    it("should detect multiple imports on one line", () => {
      const code = `import os, sys, re`;
      const imports = detectPythonImports(code);
      expect(imports.has("os")).toBe(true);
      expect(imports.has("sys")).toBe(true);
      expect(imports.has("re")).toBe(true);
    });

    it("should detect from X import statements", () => {
      const code = `from numpy import array, zeros`;
      const imports = detectPythonImports(code);
      expect(imports.has("numpy")).toBe(true);
    });

    it("should detect from X.submodule import statements", () => {
      const code = `from sklearn.model_selection import train_test_split`;
      const imports = detectPythonImports(code);
      expect(imports.has("sklearn")).toBe(true);
    });

    it("should detect PIL import", () => {
      const code = `from PIL import Image`;
      const imports = detectPythonImports(code);
      expect(imports.has("PIL")).toBe(true);
    });

    it("should detect multiple import types in the same code", () => {
      const code = `
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.linear_model import LinearRegression
from scipy.stats import norm
`;
      const imports = detectPythonImports(code);
      expect(imports.has("numpy")).toBe(true);
      expect(imports.has("pandas")).toBe(true);
      expect(imports.has("matplotlib")).toBe(true);
      expect(imports.has("sklearn")).toBe(true);
      expect(imports.has("scipy")).toBe(true);
    });

    it("should not detect commented imports", () => {
      const code = `
# import pandas
# from numpy import array
`;
      const imports = detectPythonImports(code);
      // Comments are at line start, but our regex matches "# import" which starts with #
      // The regex uses ^\s*import which won't match if there's a # before
      expect(imports.has("pandas")).toBe(false);
    });

    it("should handle indented imports (inside functions)", () => {
      const code = `
def load_data():
    import pandas as pd
    return pd.read_csv("data.csv")
`;
      const imports = detectPythonImports(code);
      expect(imports.has("pandas")).toBe(true);
    });
  });

  describe("PYODIDE_IMPORT_TO_PACKAGE mapping", () => {
    it("should map common aliases", () => {
      expect(PYODIDE_IMPORT_TO_PACKAGE["np"]).toBe("numpy");
      expect(PYODIDE_IMPORT_TO_PACKAGE["pd"]).toBe("pandas");
      expect(PYODIDE_IMPORT_TO_PACKAGE["plt"]).toBe("matplotlib");
      expect(PYODIDE_IMPORT_TO_PACKAGE["nx"]).toBe("networkx");
    });

    it("should map PIL to pillow", () => {
      expect(PYODIDE_IMPORT_TO_PACKAGE["PIL"]).toBe("pillow");
      expect(PYODIDE_IMPORT_TO_PACKAGE["pillow"]).toBe("pillow");
    });

    it("should map sklearn to scikit-learn", () => {
      expect(PYODIDE_IMPORT_TO_PACKAGE["sklearn"]).toBe("scikit-learn");
    });
  });

  describe("PYODIDE_CORE_PACKAGES", () => {
    it("should include numpy and matplotlib", () => {
      expect(PYODIDE_CORE_PACKAGES).toContain("numpy");
      expect(PYODIDE_CORE_PACKAGES).toContain("matplotlib");
    });
  });

  describe("PYODIDE_LAZY_PACKAGES", () => {
    it("should have dependencies for seaborn", () => {
      expect(PYODIDE_LAZY_PACKAGES["seaborn"]).toContain("seaborn");
      expect(PYODIDE_LAZY_PACKAGES["seaborn"]).toContain("pandas");
    });

    it("should have dependencies for statsmodels", () => {
      expect(PYODIDE_LAZY_PACKAGES["statsmodels"]).toContain("statsmodels");
      expect(PYODIDE_LAZY_PACKAGES["statsmodels"]).toContain("pandas");
    });
  });

  describe("package state management", () => {
    it("should have core packages loaded by default", () => {
      const loaded = getLoadedPackages();
      expect(loaded.has("numpy")).toBe(true);
      expect(loaded.has("matplotlib")).toBe(true);
    });

    it("should mark packages as loaded", () => {
      expect(isPackageLoaded("pandas")).toBe(false);
      markPackagesLoaded(["pandas"]);
      expect(isPackageLoaded("pandas")).toBe(true);
    });

    it("should reset loaded packages", () => {
      markPackagesLoaded(["pandas", "scipy"]);
      expect(isPackageLoaded("pandas")).toBe(true);
      expect(isPackageLoaded("scipy")).toBe(true);

      resetLoadedPackages();

      expect(isPackageLoaded("pandas")).toBe(false);
      expect(isPackageLoaded("scipy")).toBe(false);
      // Core packages should still be marked
      expect(isPackageLoaded("numpy")).toBe(true);
      expect(isPackageLoaded("matplotlib")).toBe(true);
    });
  });

  describe("getRequiredPackages", () => {
    it("should return empty for code with only core packages", () => {
      const code = `
import numpy as np
import matplotlib.pyplot as plt
`;
      const required = getRequiredPackages(code);
      expect(required).toHaveLength(0);
    });

    it("should return pandas for code that uses it", () => {
      const code = `
import pandas as pd
df = pd.DataFrame()
`;
      const required = getRequiredPackages(code);
      expect(required).toContain("pandas");
    });

    it("should not return already loaded packages", () => {
      markPackagesLoaded(["pandas"]);
      const code = `import pandas as pd`;
      const required = getRequiredPackages(code);
      expect(required).not.toContain("pandas");
    });

    it("should return scikit-learn for sklearn import", () => {
      const code = `from sklearn.linear_model import LinearRegression`;
      const required = getRequiredPackages(code);
      expect(required).toContain("scikit-learn");
    });

    it("should return pillow for PIL import", () => {
      const code = `from PIL import Image`;
      const required = getRequiredPackages(code);
      expect(required).toContain("pillow");
    });

    it("should include dependencies for seaborn", () => {
      const code = `import seaborn as sns`;
      const required = getRequiredPackages(code);
      expect(required).toContain("seaborn");
      expect(required).toContain("pandas"); // dependency
    });

    it("should not duplicate dependencies if already loaded", () => {
      markPackagesLoaded(["pandas"]);
      const code = `import seaborn as sns`;
      const required = getRequiredPackages(code);
      expect(required).toContain("seaborn");
      expect(required).not.toContain("pandas"); // already loaded
    });

    it("should handle multiple packages", () => {
      const code = `
import pandas as pd
import scipy
from sympy import symbols
from networkx import Graph
`;
      const required = getRequiredPackages(code);
      expect(required).toContain("pandas");
      expect(required).toContain("scipy");
      expect(required).toContain("sympy");
      expect(required).toContain("networkx");
    });

    it("should ignore unknown imports", () => {
      const code = `
import os
import sys
import unknown_package
`;
      const required = getRequiredPackages(code);
      expect(required).toHaveLength(0);
    });
  });
});
