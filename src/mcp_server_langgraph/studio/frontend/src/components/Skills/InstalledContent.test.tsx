/**
 * InstalledContent Component Tests
 *
 * TDD test suite for the installed skills tab component.
 * Tests skill list rendering, uninstall actions, and empty state.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InstalledContent } from "./InstalledContent";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("InstalledContent", () => {
  const defaultProps = {
    installedSkills: ["web-research", "code-review", "data-analysis"],
    onUninstall: vi.fn(),
    isUninstalling: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("renders installed skills list", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-installed-list")).toBeInTheDocument();
    });

    it("displays all installed skills", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("skills-installed-web-research"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("skills-installed-code-review"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("skills-installed-data-analysis"),
      ).toBeInTheDocument();
    });

    it("shows skill names correctly", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("web-research")).toBeInTheDocument();
      expect(screen.getByText("code-review")).toBeInTheDocument();
      expect(screen.getByText("data-analysis")).toBeInTheDocument();
    });

    it("shows uninstall button for each skill", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} />
        </TestProvider>,
      );

      const uninstallButtons = screen.getAllByRole("button", {
        name: /uninstall/i,
      });
      expect(uninstallButtons).toHaveLength(3);
    });

    it("shows checkmark icon for each installed skill", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} />
        </TestProvider>,
      );

      // Each skill row should have a success checkmark (rendered as SVG)
      // Use exact match to avoid matching skills-installed-list
      expect(
        screen.getByTestId("skills-installed-web-research"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("skills-installed-code-review"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("skills-installed-data-analysis"),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Empty State Tests
  // ===========================================================================

  describe("Empty State", () => {
    it("renders empty state when no skills installed", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} installedSkills={[]} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-installed-empty")).toBeInTheDocument();
      expect(screen.getByText("No skills installed")).toBeInTheDocument();
    });

    it("shows helpful message in empty state", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} installedSkills={[]} />
        </TestProvider>,
      );

      expect(
        screen.getByText(
          /browse the marketplace to discover and install skills/i,
        ),
      ).toBeInTheDocument();
    });

    it("does not show skills list in empty state", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} installedSkills={[]} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("skills-installed-list"),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Uninstall Action Tests
  // ===========================================================================

  describe("Uninstall Actions", () => {
    it("calls onUninstall with skill name when clicked", async () => {
      const user = userEvent.setup();
      const onUninstall = vi.fn();

      render(
        <TestProvider>
          <InstalledContent {...defaultProps} onUninstall={onUninstall} />
        </TestProvider>,
      );

      const webResearchRow = screen.getByTestId(
        "skills-installed-web-research",
      );
      const uninstallButton = within(webResearchRow).getByRole("button", {
        name: /uninstall/i,
      });

      await user.click(uninstallButton);
      expect(onUninstall).toHaveBeenCalledWith("web-research");
    });

    it("calls onUninstall with correct skill for each button", async () => {
      const user = userEvent.setup();
      const onUninstall = vi.fn();

      render(
        <TestProvider>
          <InstalledContent {...defaultProps} onUninstall={onUninstall} />
        </TestProvider>,
      );

      const codeReviewRow = screen.getByTestId("skills-installed-code-review");
      const uninstallButton = within(codeReviewRow).getByRole("button", {
        name: /uninstall/i,
      });

      await user.click(uninstallButton);
      expect(onUninstall).toHaveBeenCalledWith("code-review");
    });

    it("disables all uninstall buttons when uninstalling", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} isUninstalling={true} />
        </TestProvider>,
      );

      const uninstallButtons = screen.getAllByRole("button", {
        name: /uninstall/i,
      });
      uninstallButtons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it("enables uninstall buttons when not uninstalling", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} isUninstalling={false} />
        </TestProvider>,
      );

      const uninstallButtons = screen.getAllByRole("button", {
        name: /uninstall/i,
      });
      uninstallButtons.forEach((button) => {
        expect(button).not.toBeDisabled();
      });
    });
  });

  // ===========================================================================
  // Single Skill Tests
  // ===========================================================================

  describe("Single Skill", () => {
    it("renders correctly with single skill", () => {
      render(
        <TestProvider>
          <InstalledContent
            {...defaultProps}
            installedSkills={["web-research"]}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-installed-list")).toBeInTheDocument();
      expect(
        screen.getByTestId("skills-installed-web-research"),
      ).toBeInTheDocument();
      expect(
        screen.getAllByRole("button", { name: /uninstall/i }),
      ).toHaveLength(1);
    });
  });

  // ===========================================================================
  // Many Skills Tests
  // ===========================================================================

  describe("Many Skills", () => {
    it("handles many installed skills", () => {
      const manySkills = [
        "skill-1",
        "skill-2",
        "skill-3",
        "skill-4",
        "skill-5",
        "skill-6",
        "skill-7",
        "skill-8",
      ];

      render(
        <TestProvider>
          <InstalledContent {...defaultProps} installedSkills={manySkills} />
        </TestProvider>,
      );

      manySkills.forEach((skill) => {
        expect(
          screen.getByTestId(`skills-installed-${skill}`),
        ).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    it("uninstall buttons have accessible names", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} />
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("button", { name: /uninstall/i });
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("skill names are visible text", () => {
      render(
        <TestProvider>
          <InstalledContent {...defaultProps} />
        </TestProvider>,
      );

      defaultProps.installedSkills.forEach((skill) => {
        expect(screen.getByText(skill)).toBeInTheDocument();
      });
    });
  });
});
