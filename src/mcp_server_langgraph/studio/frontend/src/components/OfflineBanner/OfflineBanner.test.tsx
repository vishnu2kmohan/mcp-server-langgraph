/**
 * OfflineBanner Component Tests
 *
 * Sprint 3 - Phase 2.3: Offline Resilience Enhancement
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { OfflineBanner } from "./OfflineBanner";

import { TestProvider } from "@/test-utils";

describe("OfflineBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders when offline", () => {
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} />
        </TestProvider>,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/offline/i)).toBeInTheDocument();
    });

    it("does not render when online", () => {
      render(
        <TestProvider>
          <OfflineBanner isOffline={false} />
        </TestProvider>,
      );
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("shows pending count when provided", () => {
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} pendingCount={5} />
        </TestProvider>,
      );
      expect(screen.getByText(/5/)).toBeInTheDocument();
      expect(screen.getByText(/pending/i)).toBeInTheDocument();
    });

    it("hides pending count when zero", () => {
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} pendingCount={0} />
        </TestProvider>,
      );
      expect(screen.queryByText(/pending/i)).not.toBeInTheDocument();
    });
  });

  describe("sync button", () => {
    it("shows sync button when onSync is provided", () => {
      const onSync = vi.fn();
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} pendingCount={3} onSync={onSync} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /sync/i })).toBeInTheDocument();
    });

    it("calls onSync when sync button clicked", () => {
      const onSync = vi.fn();
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} pendingCount={3} onSync={onSync} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /sync/i }));
      expect(onSync).toHaveBeenCalledTimes(1);
    });

    it("disables sync button when syncing", () => {
      const onSync = vi.fn();
      render(
        <TestProvider>
          <OfflineBanner
            isOffline={true}
            pendingCount={3}
            onSync={onSync}
            isSyncing={true}
          />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /syncing/i });
      expect(button).toBeDisabled();
    });

    it("hides sync button when online and no pending", () => {
      const onSync = vi.fn();
      render(
        <TestProvider>
          <OfflineBanner isOffline={false} pendingCount={0} onSync={onSync} />
        </TestProvider>,
      );
      expect(screen.queryByRole("button")).not.toBeInTheDocument();
    });
  });

  describe("dismiss", () => {
    it("shows dismiss button when onDismiss provided", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} onDismiss={onDismiss} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /dismiss/i }),
      ).toBeInTheDocument();
    });

    it("calls onDismiss when dismiss clicked", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} onDismiss={onDismiss} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("last sync time", () => {
    it("shows last sync time when provided", () => {
      const lastSyncTime = new Date("2025-12-20T10:00:00Z");
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} lastSyncTime={lastSyncTime} />
        </TestProvider>,
      );
      expect(screen.getByText(/last sync/i)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has role alert", () => {
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} />
        </TestProvider>,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("has aria-live polite", () => {
      render(
        <TestProvider>
          <OfflineBanner isOffline={true} />
        </TestProvider>,
      );
      expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "polite");
    });
  });
});
