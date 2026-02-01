/**
 * SkillCard Tests
 *
 * TDD tests for the skill card component.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SkillCard } from "./SkillCard";
import type { SkillMetadata } from "../../types/skills";

const mockSkill: SkillMetadata = {
  name: "web-research",
  description: "Search the web for information",
  version: "1.0.0",
  author: "Anthropic",
  tags: ["research", "web", "search"],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SkillCard", () => {
  it("should display skill name", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByText("web-research")).toBeInTheDocument();
  });

  it("should display skill description", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(
      screen.getByText("Search the web for information"),
    ).toBeInTheDocument();
  });

  it("should display version badge", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByText("v1.0.0")).toBeInTheDocument();
  });

  it("should display up to 3 tags", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByText("research")).toBeInTheDocument();
    expect(screen.getByText("web")).toBeInTheDocument();
    expect(screen.getByText("search")).toBeInTheDocument();
  });

  it("should show Install button when not installed", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(
      screen.getByRole("button", { name: /install/i }),
    ).toBeInTheDocument();
  });

  it("should show Installed badge when installed", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={true}
        onInstall={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByText("Installed")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /install/i }),
    ).not.toBeInTheDocument();
  });

  it("should call onInstall when Install button clicked", () => {
    const onInstall = vi.fn();
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={onInstall}
        isInstalling={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /install/i }));
    expect(onInstall).toHaveBeenCalledTimes(1);
  });

  it("should disable Install button when installing", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={true}
      />,
    );
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("should show loading spinner when installing", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={true}
      />,
    );
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("should have data-testid for testing", () => {
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={false}
      />,
    );
    expect(screen.getByTestId("skills-card-web-research")).toBeInTheDocument();
  });

  it("should call onViewDetails when card is clicked", () => {
    const onViewDetails = vi.fn();
    render(
      <SkillCard
        skill={mockSkill}
        isInstalled={false}
        onInstall={vi.fn()}
        isInstalling={false}
        onViewDetails={onViewDetails}
      />,
    );
    // Click on card (not the button)
    const card = screen.getByTestId("skills-card-web-research");
    fireEvent.click(card);
    expect(onViewDetails).toHaveBeenCalledWith(mockSkill);
  });
});
