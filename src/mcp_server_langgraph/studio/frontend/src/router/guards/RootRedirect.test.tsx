/**
 * RootRedirect Tests
 *
 * Tests for the root redirect component.
 * RootRedirect always redirects to /studio.
 * The StudioShellGuard handles which shell layout to render.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { RootRedirect } from "./RootRedirect";

// =============================================================================
// Test Helpers
// =============================================================================

function renderWithRouter(initialPath: string = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route
          path="/studio"
          element={<div data-testid="studio">Studio</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("RootRedirect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("redirects from / to /studio", () => {
    renderWithRouter("/");

    expect(screen.getByTestId("studio")).toBeInTheDocument();
  });
});
