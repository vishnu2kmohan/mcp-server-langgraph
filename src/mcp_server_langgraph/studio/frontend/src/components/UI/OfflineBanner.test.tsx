/**
 * OfflineBanner Component Tests
 *
 * TDD tests for the offline indicator banner used in PWA support.
 * Tests cover:
 * - Visibility based on online/offline status
 * - Accessibility attributes
 * - Visual styling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { OfflineBanner } from "./OfflineBanner";

// Mock the useOffline hook
vi.mock("../../hooks/useOffline", () => ({
  useOffline: vi.fn(),
}));

import { useOffline } from "../../hooks/useOffline";

const mockUseOffline = vi.mocked(useOffline);

describe("OfflineBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("Online State", () => {
    beforeEach(() => {
      mockUseOffline.mockReturnValue(false);
    });

    it("should not render banner when online", () => {
      render(<OfflineBanner />);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("should not render any visible content when online", () => {
      const { container } = render(<OfflineBanner />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Offline State", () => {
    beforeEach(() => {
      mockUseOffline.mockReturnValue(true);
    });

    it("should render banner when offline", () => {
      render(<OfflineBanner />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should display offline message", () => {
      render(<OfflineBanner />);
      expect(
        screen.getByText(/you are currently offline/i),
      ).toBeInTheDocument();
    });

    it("should have appropriate warning styling", () => {
      render(<OfflineBanner />);
      const banner = screen.getByRole("alert");
      expect(banner).toHaveClass("bg-yellow-500");
    });

    it("should be accessible with aria-live attribute", () => {
      render(<OfflineBanner />);
      const banner = screen.getByRole("alert");
      expect(banner).toHaveAttribute("aria-live", "polite");
    });

    it("should display wifi-off icon", () => {
      render(<OfflineBanner />);
      expect(screen.getByTestId("wifi-off-icon")).toBeInTheDocument();
    });

    it("should be fixed at top of viewport", () => {
      render(<OfflineBanner />);
      const banner = screen.getByRole("alert");
      expect(banner).toHaveClass("fixed");
      expect(banner).toHaveClass("top-0");
    });

    it("should have full width", () => {
      render(<OfflineBanner />);
      const banner = screen.getByRole("alert");
      expect(banner).toHaveClass("w-full");
    });

    it("should have high z-index to appear above other content", () => {
      render(<OfflineBanner />);
      const banner = screen.getByRole("alert");
      // z-[70] is the standardized system alert z-index level
      expect(banner).toHaveClass("z-[70]");
    });
  });

  describe("Transition Behavior", () => {
    it("should hide when coming back online", () => {
      // Start offline
      mockUseOffline.mockReturnValue(true);
      const { rerender } = render(<OfflineBanner />);
      expect(screen.getByRole("alert")).toBeInTheDocument();

      // Go online
      mockUseOffline.mockReturnValue(false);
      rerender(<OfflineBanner />);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("should show when going offline", () => {
      // Start online
      mockUseOffline.mockReturnValue(false);
      const { rerender } = render(<OfflineBanner />);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();

      // Go offline
      mockUseOffline.mockReturnValue(true);
      rerender(<OfflineBanner />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });
});
