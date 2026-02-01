/**
 * RouteErrorBoundary Tests
 *
 * TDD tests for the React Router error boundary component.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { RouteErrorBoundary } from "./RouteErrorBoundary";

// Component that throws an error
function ThrowingComponent(): JSX.Element {
  throw new Error("Test error message");
}

// Component that renders normally
function NormalComponent(): JSX.Element {
  return <div data-testid="normal-content">Normal content</div>;
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RouteErrorBoundary", () => {
  it("should display error message when route throws", () => {
    const router = createMemoryRouter([
      {
        path: "/",
        element: <ThrowingComponent />,
        errorElement: <RouteErrorBoundary />,
      },
    ]);

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText(/Test error message/)).toBeInTheDocument();
  });

  it("should have a retry button", () => {
    const router = createMemoryRouter([
      {
        path: "/",
        element: <ThrowingComponent />,
        errorElement: <RouteErrorBoundary />,
      },
    ]);

    render(<RouterProvider router={router} />);

    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });

  it("should have a go home button", () => {
    const router = createMemoryRouter([
      {
        path: "/",
        element: <ThrowingComponent />,
        errorElement: <RouteErrorBoundary />,
      },
    ]);

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("link", { name: /go home/i })).toBeInTheDocument();
  });

  it("should display 404 for route not found errors", () => {
    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: <NormalComponent />,
          errorElement: <RouteErrorBoundary />,
        },
      ],
      { initialEntries: ["/non-existent-route"] },
    );

    render(<RouterProvider router={router} />);

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });

  it("should have accessible error alert", () => {
    const router = createMemoryRouter([
      {
        path: "/",
        element: <ThrowingComponent />,
        errorElement: <RouteErrorBoundary />,
      },
    ]);

    render(<RouterProvider router={router} />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
  });

  it("should have data-testid for testing", () => {
    const router = createMemoryRouter([
      {
        path: "/",
        element: <ThrowingComponent />,
        errorElement: <RouteErrorBoundary />,
      },
    ]);

    render(<RouterProvider router={router} />);

    expect(screen.getByTestId("route-error-boundary")).toBeInTheDocument();
  });
});
