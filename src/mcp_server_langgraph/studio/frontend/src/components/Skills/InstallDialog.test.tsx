/**
 * InstallDialog Tests
 *
 * TDD tests for the skill installation confirmation dialog.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InstallDialog } from "./InstallDialog";
import type { SkillMetadata } from "../../types/skills";

const mockSkill: SkillMetadata = {
  name: "web-research",
  description: "Search the web for information",
  version: "1.0.0",
  author: "Anthropic",
  tags: ["research", "web"],
};

describe("InstallDialog", () => {
  it("should not render when skill is null", () => {
    render(
      <InstallDialog
        skill={null}
        isOpen={false}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("should not render when isOpen is false", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={false}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("should render dialog when open with skill", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("should display confirmation title", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByText(/install skill/i)).toBeInTheDocument();
  });

  it("should display skill name in message", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByText(/web-research/)).toBeInTheDocument();
  });

  it("should display version info", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByText(/1.0.0/)).toBeInTheDocument();
  });

  it("should have Cancel button", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("should have Install button", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(
      screen.getByRole("button", { name: /install/i }),
    ).toBeInTheDocument();
  });

  it("should call onClose when Cancel clicked", () => {
    const onClose = vi.fn();
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={onClose}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("should call onConfirm when Install clicked", () => {
    const onConfirm = vi.fn();
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        isInstalling={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /install/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("should disable buttons when installing", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={true}
      />,
    );
    expect(screen.getByRole("button", { name: /installing/i })).toBeDisabled();
  });

  it("should show loading state when installing", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={true}
      />,
    );
    // Should show installing text (may appear in multiple places)
    const installingElements = screen.getAllByText(/installing/i);
    expect(installingElements.length).toBeGreaterThan(0);
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("should have accessible dialog", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  });

  it("should have data-testid", () => {
    render(
      <InstallDialog
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByTestId("install-dialog")).toBeInTheDocument();
  });

  // ===========================================================================
  // Enhanced Loading State Tests
  // ===========================================================================

  describe("Enhanced Loading States", () => {
    it("should show progress indicator when installing", () => {
      render(
        <InstallDialog
          skill={mockSkill}
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isInstalling={true}
        />,
      );
      expect(screen.getByTestId("install-progress")).toBeInTheDocument();
    });

    it("should show progress message when installing", () => {
      render(
        <InstallDialog
          skill={mockSkill}
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isInstalling={true}
        />,
      );
      // Should show a helpful progress message
      expect(
        screen.getByTestId("install-progress-message"),
      ).toBeInTheDocument();
    });

    it("should hide progress indicator when not installing", () => {
      render(
        <InstallDialog
          skill={mockSkill}
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
          isInstalling={false}
        />,
      );
      expect(screen.queryByTestId("install-progress")).not.toBeInTheDocument();
    });
  });
});
