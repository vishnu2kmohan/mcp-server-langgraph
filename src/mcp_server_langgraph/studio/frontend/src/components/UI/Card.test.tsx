/**
 * Card Component Tests
 *
 * Tests for the Card primitive component and its subcomponents.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "./Card";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Card", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(<Card data-testid="card">Content</Card>);
      expect(screen.getByTestId("card")).toBeInTheDocument();
      expect(screen.getByText("Content")).toBeInTheDocument();
    });

    it("renders children correctly", () => {
      render(
        <Card data-testid="card">
          <div data-testid="child">Child Content</div>
        </Card>,
      );
      expect(screen.getByTestId("child")).toBeInTheDocument();
    });
  });

  describe("variants", () => {
    it("renders default variant with border", () => {
      render(
        <Card variant="default" data-testid="card">
          Default
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("border");
    });

    it("renders elevated variant with shadow", () => {
      render(
        <Card variant="elevated" data-testid="card">
          Elevated
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("shadow-elevated");
    });

    it("renders ghost variant without border", () => {
      render(
        <Card variant="ghost" data-testid="card">
          Ghost
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("border-transparent");
    });
  });

  describe("padding", () => {
    it("renders with no padding", () => {
      render(
        <Card padding="none" data-testid="card">
          No Padding
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-0");
    });

    it("renders with small padding", () => {
      render(
        <Card padding="sm" data-testid="card">
          Small Padding
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-3");
    });

    it("renders with medium padding (default)", () => {
      render(
        <Card padding="md" data-testid="card">
          Medium Padding
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-4");
    });

    it("renders with large padding", () => {
      render(
        <Card padding="lg" data-testid="card">
          Large Padding
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("p-6");
    });
  });

  describe("interactive", () => {
    it("applies hover styles when interactive", () => {
      render(
        <Card interactive data-testid="card">
          Interactive
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("cursor-pointer");
    });

    it("does not apply hover styles when not interactive", () => {
      render(
        <Card interactive={false} data-testid="card">
          Not Interactive
        </Card>,
      );
      expect(screen.getByTestId("card")).not.toHaveClass("cursor-pointer");
    });

    it("handles click events when interactive", () => {
      const handleClick = vi.fn();
      render(
        <Card interactive onClick={handleClick} data-testid="card">
          Clickable
        </Card>,
      );
      fireEvent.click(screen.getByTestId("card"));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <Card className="custom-class" data-testid="card">
          Custom
        </Card>,
      );
      expect(screen.getByTestId("card")).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(<Card data-testid="custom-card">Props</Card>);
      expect(screen.getByTestId("custom-card")).toBeInTheDocument();
    });
  });
});

describe("CardHeader", () => {
  it("renders children", () => {
    render(<CardHeader>Header Content</CardHeader>);
    expect(screen.getByText("Header Content")).toBeInTheDocument();
  });

  it("applies header styling", () => {
    render(<CardHeader data-testid="header">Header</CardHeader>);
    expect(screen.getByTestId("header")).toHaveClass("flex");
  });
});

describe("CardTitle", () => {
  it("renders as h3 by default", () => {
    render(<CardTitle>Title</CardTitle>);
    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
      "Title",
    );
  });

  it("applies title styling", () => {
    render(<CardTitle>Styled Title</CardTitle>);
    expect(screen.getByText("Styled Title")).toHaveClass("font-semibold");
  });
});

describe("CardContent", () => {
  it("renders children", () => {
    render(<CardContent>Body Content</CardContent>);
    expect(screen.getByText("Body Content")).toBeInTheDocument();
  });
});

describe("CardFooter", () => {
  it("renders children", () => {
    render(<CardFooter>Footer Content</CardFooter>);
    expect(screen.getByText("Footer Content")).toBeInTheDocument();
  });

  it("applies footer styling", () => {
    render(<CardFooter data-testid="footer">Footer</CardFooter>);
    expect(screen.getByTestId("footer")).toHaveClass("border-t");
  });
});

describe("Card composition", () => {
  it("composes all subcomponents correctly", () => {
    render(
      <Card data-testid="card">
        <CardHeader>
          <CardTitle>My Card</CardTitle>
        </CardHeader>
        <CardContent>Card body content</CardContent>
        <CardFooter>Card footer</CardFooter>
      </Card>,
    );

    expect(screen.getByText("My Card")).toBeInTheDocument();
    expect(screen.getByText("Card body content")).toBeInTheDocument();
    expect(screen.getByText("Card footer")).toBeInTheDocument();
  });
});
