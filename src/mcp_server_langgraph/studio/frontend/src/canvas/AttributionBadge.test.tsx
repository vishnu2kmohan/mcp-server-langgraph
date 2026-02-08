/**
 * AttributionBadge Component Tests
 *
 * TDD: Tests written first to define expected behavior
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { AttributionBadge } from "./AttributionBadge";
import type { EditMetadata } from "../types/artifacts";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AttributionBadge", () => {
  describe("getAttributionType helper", () => {
    it('should return "user-created" when metadata is undefined', () => {
      render(
        <TestProvider>
          <AttributionBadge metadata={undefined} />
        </TestProvider>,
      );
      expect(screen.getByText("User-created")).toBeInTheDocument();
    });

    it('should return "ai-generated" when origin is ai and not modified', () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: false,
        lastEditedBy: "ai",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      expect(screen.getByText("AI-generated")).toBeInTheDocument();
    });

    it('should return "user-modified" when origin is ai and modified is true', () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: true,
        lastEditedBy: "user",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      expect(screen.getByText("User-modified")).toBeInTheDocument();
    });

    it('should return "user-created" when origin is user', () => {
      const metadata: EditMetadata = {
        origin: "user",
        modified: false,
        lastEditedBy: "user",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      expect(screen.getByText("User-created")).toBeInTheDocument();
    });

    it('should return "user-created" when origin is user even if modified', () => {
      const metadata: EditMetadata = {
        origin: "user",
        modified: true,
        lastEditedBy: "user",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      expect(screen.getByText("User-created")).toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("should have insight colors for AI-generated badge", () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: false,
        lastEditedBy: "ai",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      const badge = screen.getByText("AI-generated").closest("span");
      expect(badge).toHaveClass("bg-insight-3");
      expect(badge).toHaveClass("text-insight-11");
    });

    it("should have primary colors for User-modified badge", () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: true,
        lastEditedBy: "user",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      const badge = screen.getByText("User-modified").closest("span");
      expect(badge).toHaveClass("bg-primary-3");
      expect(badge).toHaveClass("text-primary-11");
    });

    it("should have neutral colors for User-created badge", () => {
      const metadata: EditMetadata = {
        origin: "user",
        modified: false,
        lastEditedBy: "user",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      const badge = screen.getByText("User-created").closest("span");
      expect(badge).toHaveClass("bg-neutral-2");
      expect(badge).toHaveClass("text-neutral-11");
    });
  });

  describe("icons", () => {
    it("should show sparkles icon for AI-generated", () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: false,
        lastEditedBy: "ai",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      expect(screen.getByTestId("sparkles-icon")).toBeInTheDocument();
    });

    it("should show pencil icon for User-modified", () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: true,
        lastEditedBy: "user",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} />
        </TestProvider>,
      );
      expect(screen.getByTestId("pencil-icon")).toBeInTheDocument();
    });

    it("should show user icon for User-created", () => {
      render(
        <TestProvider>
          <AttributionBadge metadata={undefined} />
        </TestProvider>,
      );
      expect(screen.getByTestId("user-icon")).toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("should only show icon in compact mode", () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: false,
        lastEditedBy: "ai",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} compact />
        </TestProvider>,
      );
      expect(screen.getByTestId("sparkles-icon")).toBeInTheDocument();
      expect(screen.queryByText("AI-generated")).not.toBeInTheDocument();
    });

    it("should have aria-label in compact mode for accessibility", () => {
      const metadata: EditMetadata = {
        origin: "ai",
        modified: false,
        lastEditedBy: "ai",
      };
      render(
        <TestProvider>
          <AttributionBadge metadata={metadata} compact />
        </TestProvider>,
      );
      const badge = screen.getByLabelText("AI-generated");
      expect(badge).toBeInTheDocument();
    });
  });
});
