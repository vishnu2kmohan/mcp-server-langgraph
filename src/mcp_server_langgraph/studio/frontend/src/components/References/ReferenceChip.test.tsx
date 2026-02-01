/**
 * Tests for ReferenceChip component
 *
 * TDD: Tests written first per project guidelines.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReferenceChip } from "./ReferenceChip";
import { ReferenceResolverProvider as _ReferenceResolverProvider } from "@/contexts/ReferenceResolverContext";
import type { ResolvedReference } from "@/types/references";

// Mock the context provider for isolated tests
const mockResolvedRefs = new Map<string, ResolvedReference>();

vi.mock("@/contexts/ReferenceResolverContext", async () => {
  const actual = await vi.importActual("@/contexts/ReferenceResolverContext");
  return {
    ...actual,
    useReferenceResolver: () => ({
      resolvedRefs: mockResolvedRefs,
      isLoading: false,
      error: undefined,
    }),
  };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ReferenceChip", () => {
  beforeEach(() => {
    mockResolvedRefs.clear();
  });

  describe("rendering", () => {
    it("should render tool reference with wrench icon", () => {
      render(
        <ReferenceChip type="tool" qualifier="filesystem" id="read_file" />,
      );

      expect(screen.getByText("read_file")).toBeInTheDocument();
      // Check for the SVG icon (wrench)
      const chip = screen.getByRole("button");
      expect(chip).toHaveClass("bg-primary-3");
    });

    it("should render skill reference with sparkles icon", () => {
      render(
        <ReferenceChip type="skill" qualifier="code-review" id="code-review" />,
      );

      expect(screen.getByText("code-review")).toBeInTheDocument();
      const chip = screen.getByRole("button");
      expect(chip).toHaveClass("bg-success-3");
    });

    it("should render artifact reference with file icon", () => {
      render(
        <ReferenceChip type="artifact" qualifier="chart-123" id="chart-123" />,
      );

      expect(screen.getByText("chart-123")).toBeInTheDocument();
      const chip = screen.getByRole("button");
      expect(chip).toHaveClass("bg-neutral-3");
    });

    it("should render memory reference with brain icon (Phase 4)", () => {
      render(
        <ReferenceChip type="memory" qualifier="note-123" id="note-123" />,
      );

      expect(screen.getByText("note-123")).toBeInTheDocument();
      const chip = screen.getByRole("button");
      // Memory refs use info color (cyan/blue tint)
      expect(chip).toHaveClass("bg-info-3");
    });

    it("should render plan reference with list icon (Phase 4)", () => {
      render(<ReferenceChip type="plan" qualifier="plan-456" id="plan-456" />);

      expect(screen.getByText("plan-456")).toBeInTheDocument();
      const chip = screen.getByRole("button");
      // Plan refs use warning color (amber/orange tint)
      expect(chip).toHaveClass("bg-warning-3");
    });

    it("should use custom label when provided", () => {
      render(
        <ReferenceChip
          type="tool"
          qualifier="fs"
          id="read"
          label="Read File"
        />,
      );

      expect(screen.getByText("Read File")).toBeInTheDocument();
    });
  });

  describe("resolved state", () => {
    it("should display resolved name from context", () => {
      mockResolvedRefs.set("tool:filesystem:read_file", {
        type: "tool",
        qualifier: "filesystem",
        id: "read_file",
        displayName: "Read File Tool",
        description: "Reads a file from the filesystem",
        status: "valid",
      });

      render(
        <ReferenceChip type="tool" qualifier="filesystem" id="read_file" />,
      );

      // Should show resolved displayName
      expect(screen.getByText("Read File Tool")).toBeInTheDocument();
    });

    it("should show not_found styling for missing references", () => {
      mockResolvedRefs.set("tool:fs:missing", {
        type: "tool",
        qualifier: "fs",
        id: "missing",
        displayName: "missing",
        status: "not_found",
      });

      render(<ReferenceChip type="tool" qualifier="fs" id="missing" />);

      const chip = screen.getByRole("button");
      expect(chip).toHaveClass("opacity-50");
      expect(chip).toHaveClass("line-through");
    });

    it("should show unauthorized styling for forbidden references", () => {
      mockResolvedRefs.set("artifact:secret:data", {
        type: "artifact",
        qualifier: "secret",
        id: "data",
        displayName: "data",
        status: "unauthorized",
      });

      render(<ReferenceChip type="artifact" qualifier="secret" id="data" />);

      const chip = screen.getByRole("button");
      expect(chip).toHaveClass("opacity-50");
      expect(chip).toHaveClass("cursor-not-allowed");
    });
  });

  describe("accessibility", () => {
    it("should have accessible role", () => {
      render(<ReferenceChip type="skill" qualifier="analyze" id="analyze" />);

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("should have aria-label describing the reference", () => {
      render(<ReferenceChip type="tool" qualifier="server" id="tool_name" />);

      const chip = screen.getByRole("button");
      expect(chip).toHaveAttribute(
        "aria-label",
        "Tool reference: server:tool_name",
      );
    });

    it("should be keyboard navigable", async () => {
      const user = userEvent.setup();

      render(<ReferenceChip type="skill" qualifier="test" id="test" />);

      const chip = screen.getByRole("button");
      await user.tab();
      expect(chip).toHaveFocus();
    });
  });

  describe("tooltip/popover", () => {
    it("should show description on hover when resolved", async () => {
      const user = userEvent.setup();

      mockResolvedRefs.set("tool:fs:read", {
        type: "tool",
        qualifier: "fs",
        id: "read",
        displayName: "Read",
        description: "Reads file contents from disk",
        status: "valid",
      });

      render(<ReferenceChip type="tool" qualifier="fs" id="read" />);

      const chip = screen.getByRole("button");
      await user.hover(chip);

      // Description should appear in tooltip
      expect(
        await screen.findByText("Reads file contents from disk"),
      ).toBeInTheDocument();
    });
  });
});
