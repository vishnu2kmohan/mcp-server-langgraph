/**
 * SkillDetails Modal Tests
 *
 * TDD tests for the skill details modal component.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SkillDetails } from "./SkillDetails";
import type { SkillMetadata } from "../../types/skills";

const mockSkill: SkillMetadata = {
  name: "web-research",
  description: "Search the web for information and retrieve relevant content.",
  version: "1.0.0",
  author: "Anthropic",
  tags: ["research", "web", "search"],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SkillDetails", () => {
  it("should not render when skill is null", () => {
    render(
      <SkillDetails
        skill={null}
        isOpen={false}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("should not render when isOpen is false", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={false}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("should render dialog when open with skill", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("should display skill name as title", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.getByText("web-research")).toBeInTheDocument();
  });

  it("should display full description", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(
      screen.getByText(
        "Search the web for information and retrieve relevant content.",
      ),
    ).toBeInTheDocument();
  });

  it("should display author when available", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.getByText("Anthropic")).toBeInTheDocument();
  });

  it("should display all tags", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.getByText("research")).toBeInTheDocument();
    expect(screen.getByText("web")).toBeInTheDocument();
    expect(screen.getByText("search")).toBeInTheDocument();
  });

  it("should call onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={onClose}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("should show Install button when not installed", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(
      screen.getByRole("button", { name: /install/i }),
    ).toBeInTheDocument();
  });

  it("should show Installed badge when installed", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={true}
        isInstalling={false}
      />,
    );
    expect(screen.getByText(/installed/i)).toBeInTheDocument();
  });

  it("should have accessible dialog", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  });

  it("should have data-testid", () => {
    render(
      <SkillDetails
        skill={mockSkill}
        isOpen={true}
        onClose={vi.fn()}
        onInstall={vi.fn()}
        isInstalled={false}
        isInstalling={false}
      />,
    );
    expect(screen.getByTestId("skill-details-modal")).toBeInTheDocument();
  });
});
