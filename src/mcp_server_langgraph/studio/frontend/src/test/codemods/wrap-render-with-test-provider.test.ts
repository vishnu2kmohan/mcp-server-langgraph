/**
 * Tests for wrap-render-with-test-provider codemod
 *
 * Uses jscodeshift's applyTransform for fixture-based testing.
 * Each test case validates a specific transformation or skip condition.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { applyTransform } from "jscodeshift/src/testUtils";
import transform from "../../../scripts/codemods/wrap-render-with-test-provider";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// Helper to run transform and compare results
// jscodeshift returns empty string "" when no changes, null or empty should be treated as "no changes"
function runTransform(input: string, path = "test.test.tsx"): string | null {
  const result = applyTransform(
    { default: transform, parser: "tsx" },
    {},
    { source: input, path },
  );
  // Treat empty string as null (no changes)
  return result === "" ? null : result;
}

describe("wrap-render-with-test-provider codemod", () => {
  describe("bare-render transformation", () => {
    it("should wrap bare render(<Component />) with TestProvider", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

it("renders", () => {
  render(<MyComponent />);
  expect(screen.getByText("Hello")).toBeInTheDocument();
});
`.trim();

      const result = runTransform(input);

      expect(result).not.toBeNull();
      expect(result).toContain('import { TestProvider } from "@/test-utils"');
      expect(result).toContain(
        "render(<TestProvider><MyComponent /></TestProvider>)",
      );
    });

    it("should wrap render with props", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { Button } from "./Button";

it("renders with props", () => {
  render(<Button variant="primary" onClick={() => {}}>Click me</Button>);
});
`.trim();

      const result = runTransform(input);

      expect(result).not.toBeNull();
      expect(result).toContain('import { TestProvider } from "@/test-utils"');
      expect(result).toContain("<TestProvider><Button");
      expect(result).toContain("</Button></TestProvider>");
    });

    it("should wrap multiple render calls in same file", () => {
      const input = `
import { render, screen, cleanup } from "@testing-library/react";
import { Header } from "./Header";
import { Footer } from "./Footer";

afterEach(cleanup);

it("renders header", () => {
  render(<Header title="Test" />);
});

it("renders footer", () => {
  render(<Footer />);
});
`.trim();

      const result = runTransform(input);

      expect(result).not.toBeNull();
      // Should have exactly one TestProvider import
      const importMatches = result!.match(/import.*TestProvider.*from/g);
      expect(importMatches?.length).toBe(1);
      // Both render calls should be wrapped
      expect(result).toContain("<TestProvider><Header");
      expect(result).toContain("<TestProvider><Footer");
    });
  });

  describe("already-wrapped-testprovider", () => {
    it("should not change render already wrapped with TestProvider", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { TestProvider } from "@/test-utils";
import { MyComponent } from "./MyComponent";

it("renders", () => {
  render(<TestProvider><MyComponent /></TestProvider>);
});
`.trim();

      const result = runTransform(input);
      // Should return null (no changes)
      expect(result).toBeNull();
    });
  });

  describe("already-wrapped-provider", () => {
    it("should not change render already wrapped with Provider", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "./store";
import { MyComponent } from "./MyComponent";

it("renders", () => {
  render(<Provider store={store}><MyComponent /></Provider>);
});
`.trim();

      const result = runTransform(input);
      // Should return null (no changes)
      expect(result).toBeNull();
    });
  });

  describe("memory-router-only replacement", () => {
    it("should replace MemoryRouter wrapper with TestProvider", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { NavLink } from "./NavLink";

it("renders link", () => {
  render(<MemoryRouter><NavLink to="/home">Home</NavLink></MemoryRouter>);
});
`.trim();

      const result = runTransform(input);

      expect(result).not.toBeNull();
      // Should add TestProvider import
      expect(result).toContain('import { TestProvider } from "@/test-utils"');
      // Should wrap with TestProvider
      expect(result).toContain("<TestProvider><NavLink");
      expect(result).toContain("</NavLink></TestProvider>");
      // Should NOT have MemoryRouter in render call
      expect(result).not.toMatch(/render\(<MemoryRouter/);
    });

    it("should replace MemoryRouter with initialEntries", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { RouteComponent } from "./RouteComponent";

it("renders at route", () => {
  render(<MemoryRouter initialEntries={["/dashboard"]}><RouteComponent /></MemoryRouter>);
});
`.trim();

      const result = runTransform(input);

      expect(result).not.toBeNull();
      // Should add TestProvider import
      expect(result).toContain('import { TestProvider } from "@/test-utils"');
      // TestProvider should have initialEntries prop
      expect(result).toContain('initialEntries={["/dashboard"]}');
      expect(result).toContain("<TestProvider");
    });
  });

  describe("custom-render-function skip", () => {
    it("should skip files with renderWithProviders function", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { store } from "./store";
import { MyComponent } from "./MyComponent";

const renderWithProviders = (component: React.ReactElement) => {
  return render(<Provider store={store}>{component}</Provider>);
};

it("renders", () => {
  renderWithProviders(<MyComponent />);
});
`.trim();

      const result = runTransform(input);
      // Should skip entirely (null)
      expect(result).toBeNull();
    });

    it("should skip files with renderWithStore function", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

function renderWithStore(component: React.ReactElement) {
  return render(component);
}

it("renders", () => {
  render(<MyComponent />);
});
`.trim();

      const result = runTransform(input);
      expect(result).toBeNull();
    });

    it("should skip files with customRender function", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

const customRender = (ui: React.ReactElement) => render(ui);

it("renders", () => {
  render(<MyComponent />);
});
`.trim();

      const result = runTransform(input);
      expect(result).toBeNull();
    });
  });

  describe("vi-mock-redux skip", () => {
    it("should skip files with vi.mock for store", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

vi.mock("./store", () => ({
  useAppSelector: vi.fn(),
  useAppDispatch: vi.fn(),
}));

it("renders", () => {
  render(<MyComponent />);
});
`.trim();

      const result = runTransform(input);
      expect(result).toBeNull();
    });

    it("should skip files with vi.mock for redux hooks", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

vi.mock("../../store/hooks", () => ({
  useAppSelector: vi.fn(),
}));

it("renders", () => {
  render(<MyComponent />);
});
`.trim();

      const result = runTransform(input);
      expect(result).toBeNull();
    });

    it("should skip files with vi.mock for slice", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

vi.mock("../../store/slices/authSlice", async () => {
  const actual = await vi.importActual("../../store/slices/authSlice");
  return {
    ...actual,
    selectUser: vi.fn(),

  };
});
it("renders", () => {
  render(<MyComponent />);
});
`.trim();

      const result = runTransform(input);
      expect(result).toBeNull();
    });
  });

  describe("dynamic-render skip", () => {
    it("should not wrap render calls with variable argument", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

it("renders dynamically", () => {
  const element = <MyComponent />;
  render(element);
});
`.trim();

      const result = runTransform(input);
      // Should return null because the only render call has a dynamic argument
      expect(result).toBeNull();
    });

    it("should not wrap render calls with function call argument", () => {
      const input = `
import { render } from "@testing-library/react";
import { createComponent } from "./factory";

it("renders from factory", () => {
  render(createComponent());
});
`.trim();

      const result = runTransform(input);
      expect(result).toBeNull();
    });
  });

  describe("existing-import handling", () => {
    it("should not duplicate TestProvider import if already imported", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { TestProvider } from "@/test-utils";
import { MyComponent } from "./MyComponent";
import { OtherComponent } from "./OtherComponent";

it("first test already uses TestProvider", () => {
  render(<TestProvider><MyComponent /></TestProvider>);
});

it("second test needs wrapping", () => {
  render(<OtherComponent />);
});
`.trim();

      const result = runTransform(input);
      if (result) {
        // Count TestProvider imports - should be exactly 1
        const importMatches = result.match(/import.*TestProvider.*from/g);
        expect(importMatches?.length).toBe(1);
        // The second render should be wrapped
        expect(result).toContain("<TestProvider><OtherComponent");
      }
    });

    it("should add to existing test-utils import", () => {
      const input = `
import { render, screen } from "@testing-library/react";
import { createTestStore } from "@/test-utils";
import { MyComponent } from "./MyComponent";

it("renders", () => {
  render(<MyComponent />);
});
`.trim();

      const result = runTransform(input);
      expect(result).not.toBeNull();
      // Should have combined import with both createTestStore and TestProvider
      expect(result).toContain("createTestStore");
      expect(result).toContain("TestProvider");
      expect(result).toContain('@/test-utils"');
    });
  });

  describe("edge cases", () => {
    it("should handle self-closing JSX elements", () => {
      const input = `
import { render } from "@testing-library/react";
import { Icon } from "./Icon";

it("renders icon", () => {
  render(<Icon name="check" />);
});
`.trim();

      const result = runTransform(input);

      expect(result).not.toBeNull();
      expect(result).toContain('import { TestProvider } from "@/test-utils"');
      expect(result).toContain("<TestProvider><Icon");
    });

    it("should handle JSX fragments as children", () => {
      const input = `
import { render } from "@testing-library/react";
import { Header } from "./Header";
import { Content } from "./Content";

it("renders multiple components", () => {
  render(<><Header /><Content /></>);
});
`.trim();

      const result = runTransform(input);

      expect(result).not.toBeNull();
      expect(result).toContain('import { TestProvider } from "@/test-utils"');
      expect(result).toContain("<TestProvider><>");
      expect(result).toContain("</></TestProvider>");
    });

    it("should skip non-test files based on path", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

render(<MyComponent />);
`.trim();

      // Use a non-test file path
      const result = runTransform(input, "MyComponent.tsx");

      expect(result).toBeNull();
    });

    it("should process spec files", () => {
      const input = `
import { render } from "@testing-library/react";
import { MyComponent } from "./MyComponent";

it("renders", () => {
  render(<MyComponent />);
});
`.trim();

      const result = runTransform(input, "MyComponent.spec.tsx");

      expect(result).not.toBeNull();
      expect(result).toContain("<TestProvider>");
    });
  });
});
