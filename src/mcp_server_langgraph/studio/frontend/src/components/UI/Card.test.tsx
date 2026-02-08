/**
 * Card Component Tests
 *
 * Tests for the Card primitive component and its subcomponents.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "./Card";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Card", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(
        <TestProvider>
          <Card data-testid="card">Content</Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toBeInTheDocument();
      expect(screen.getByText("Content")).toBeInTheDocument();
    });

    it("renders children correctly", () => {
      render(
        <TestProvider>
          <Card data-testid="card">
            <div data-testid="child">Child Content</div>
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("child")).toBeInTheDocument();
    });
  });

  describe("variants", () => {
    it("renders default variant with border", () => {
      render(
        <TestProvider>
          <Card variant="default" data-testid="card">
            Default
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("border");
    });

    it("renders elevated variant with shadow", () => {
      render(
        <TestProvider>
          <Card variant="elevated" data-testid="card">
            Elevated
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("shadow-elevated");
    });

    it("renders ghost variant without border", () => {
      render(
        <TestProvider>
          <Card variant="ghost" data-testid="card">
            Ghost
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("border-transparent");
    });
  });

  describe("padding", () => {
    it("renders with no padding", () => {
      render(
        <TestProvider>
          <Card padding="none" data-testid="card">
            No Padding
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-0");
    });

    it("renders with small padding", () => {
      render(
        <TestProvider>
          <Card padding="sm" data-testid="card">
            Small Padding
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-3");
    });

    it("renders with medium padding (default)", () => {
      render(
        <TestProvider>
          <Card padding="md" data-testid="card">
            Medium Padding
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-4");
    });

    it("renders with large padding", () => {
      render(
        <TestProvider>
          <Card padding="lg" data-testid="card">
            Large Padding
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-6");
    });
  });

  describe("interactive", () => {
    it("applies hover styles when interactive", () => {
      render(
        <TestProvider>
          <Card interactive data-testid="card">
            Interactive
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("cursor-pointer");
    });

    it("does not apply hover styles when not interactive", () => {
      render(
        <TestProvider>
          <Card interactive={false} data-testid="card">
            Not Interactive
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).not.toHaveClass("cursor-pointer");
    });

    it("handles click events when interactive", () => {
      const handleClick = vi.fn();
      render(
        <TestProvider>
          <Card interactive onClick={handleClick} data-testid="card">
            Clickable
          </Card>
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("card"));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <TestProvider>
          <Card className="custom-class" data-testid="card">
            Custom
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card")).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(
        <TestProvider>
          <Card data-testid="custom-card">Props</Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("custom-card")).toBeInTheDocument();
    });
  });
});

describe("CardHeader", () => {
  it("renders children", () => {
    render(
      <TestProvider>
        <CardHeader>Header Content</CardHeader>
      </TestProvider>,
    );
    expect(screen.getByText("Header Content")).toBeInTheDocument();
  });

  it("applies header styling", () => {
    render(
      <TestProvider>
        <CardHeader data-testid="header">Header</CardHeader>
      </TestProvider>,
    );
    expect(screen.getByTestId("header")).toHaveClass("flex");
  });
});

describe("CardTitle", () => {
  it("renders as h3 by default", () => {
    render(
      <TestProvider>
        <CardTitle>Title</CardTitle>
      </TestProvider>,
    );
    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
      "Title",
    );
  });

  it("applies title styling", () => {
    render(
      <TestProvider>
        <CardTitle>Styled Title</CardTitle>
      </TestProvider>,
    );
    expect(screen.getByText("Styled Title")).toHaveClass("font-semibold");
  });
});

describe("CardContent", () => {
  it("renders children", () => {
    render(
      <TestProvider>
        <CardContent>Body Content</CardContent>
      </TestProvider>,
    );
    expect(screen.getByText("Body Content")).toBeInTheDocument();
  });
});

describe("CardFooter", () => {
  it("renders children", () => {
    render(
      <TestProvider>
        <CardFooter>Footer Content</CardFooter>
      </TestProvider>,
    );
    expect(screen.getByText("Footer Content")).toBeInTheDocument();
  });

  it("applies footer styling", () => {
    render(
      <TestProvider>
        <CardFooter data-testid="footer">Footer</CardFooter>
      </TestProvider>,
    );
    expect(screen.getByTestId("footer")).toHaveClass("border-t");
  });
});

describe("Card composition", () => {
  it("composes all subcomponents correctly", () => {
    render(
      <TestProvider>
        <Card data-testid="card">
          <CardHeader>
            <CardTitle>My Card</CardTitle>
          </CardHeader>
          <CardContent>Card body content</CardContent>
          <CardFooter>Card footer</CardFooter>
        </Card>
      </TestProvider>,
    );

    expect(screen.getByText("My Card")).toBeInTheDocument();
    expect(screen.getByText("Card body content")).toBeInTheDocument();
    expect(screen.getByText("Card footer")).toBeInTheDocument();
  });
});

describe("CVA integration", () => {
  it("exports cardVariants function for external use", async () => {
    const { cardVariants } = await import("./Card");
    expect(typeof cardVariants).toBe("function");
  });
});
