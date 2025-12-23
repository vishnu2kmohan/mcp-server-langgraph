/**
 * ActivityBar Component Tests
 *
 * Tests for the JupyterLab/VS Code-style activity bar.
 * Provides quick navigation between sidebar views.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ActivityBar, ActivityBarItem, type ActivityItem } from "./ActivityBar";
import { MessageSquare, Settings, FileText, Activity } from "lucide-react";

const mockItems: ActivityItem[] = [
  {
    id: "chat",
    icon: <MessageSquare data-testid="chat-icon" />,
    label: "Chat",
    badge: 3,
  },
  { id: "files", icon: <FileText data-testid="files-icon" />, label: "Files" },
  {
    id: "activity",
    icon: <Activity data-testid="activity-icon" />,
    label: "Activity",
  },
  {
    id: "settings",
    icon: <Settings data-testid="settings-icon" />,
    label: "Settings",
  },
];

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ActivityBar", () => {
  describe("rendering", () => {
    it("renders all activity items", () => {
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={() => {}} />,
      );

      expect(screen.getByLabelText("Chat")).toBeInTheDocument();
      expect(screen.getByLabelText("Files")).toBeInTheDocument();
      expect(screen.getByLabelText("Activity")).toBeInTheDocument();
      expect(screen.getByLabelText("Settings")).toBeInTheDocument();
    });

    it("renders icons for each item", () => {
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={() => {}} />,
      );

      expect(screen.getByTestId("chat-icon")).toBeInTheDocument();
      expect(screen.getByTestId("files-icon")).toBeInTheDocument();
    });

    it("applies vertical layout by default", () => {
      render(
        <ActivityBar
          items={mockItems}
          activeId="chat"
          onSelect={() => {}}
          data-testid="activity-bar"
        />,
      );

      expect(screen.getByTestId("activity-bar")).toHaveClass("flex-col");
    });

    it("applies horizontal layout when specified", () => {
      render(
        <ActivityBar
          items={mockItems}
          activeId="chat"
          onSelect={() => {}}
          orientation="horizontal"
          data-testid="activity-bar"
        />,
      );

      expect(screen.getByTestId("activity-bar")).toHaveClass("flex-row");
    });
  });

  describe("selection", () => {
    it("highlights active item", () => {
      render(
        <ActivityBar items={mockItems} activeId="files" onSelect={() => {}} />,
      );

      const filesButton = screen.getByLabelText("Files");
      expect(filesButton).toHaveAttribute("aria-selected", "true");
    });

    it("calls onSelect when item is clicked", () => {
      const onSelect = vi.fn();
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={onSelect} />,
      );

      fireEvent.click(screen.getByLabelText("Settings"));
      expect(onSelect).toHaveBeenCalledWith("settings");
    });

    it("does not call onSelect for already active item", () => {
      const onSelect = vi.fn();
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={onSelect} />,
      );

      fireEvent.click(screen.getByLabelText("Chat"));
      expect(onSelect).not.toHaveBeenCalled();
    });
  });

  describe("badges", () => {
    it("displays badge count when provided", () => {
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={() => {}} />,
      );

      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("does not display badge when not provided", () => {
      const itemsWithoutBadge: ActivityItem[] = [
        { id: "test", icon: <MessageSquare />, label: "Test" },
      ];
      render(
        <ActivityBar
          items={itemsWithoutBadge}
          activeId="test"
          onSelect={() => {}}
        />,
      );

      expect(screen.queryByText(/\d+/)).not.toBeInTheDocument();
    });

    it("truncates large badge numbers", () => {
      const itemsWithLargeBadge: ActivityItem[] = [
        { id: "test", icon: <MessageSquare />, label: "Test", badge: 150 },
      ];
      render(
        <ActivityBar
          items={itemsWithLargeBadge}
          activeId="test"
          onSelect={() => {}}
        />,
      );

      expect(screen.getByText("99+")).toBeInTheDocument();
    });
  });

  describe("tooltips", () => {
    it("shows label as tooltip", () => {
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={() => {}} />,
      );

      expect(screen.getByLabelText("Chat")).toHaveAttribute("title", "Chat");
    });
  });

  describe("keyboard navigation", () => {
    it("supports keyboard activation with Enter", () => {
      const onSelect = vi.fn();
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={onSelect} />,
      );

      const filesButton = screen.getByLabelText("Files");
      fireEvent.keyDown(filesButton, { key: "Enter" });
      expect(onSelect).toHaveBeenCalledWith("files");
    });

    it("supports keyboard activation with Space", () => {
      const onSelect = vi.fn();
      render(
        <ActivityBar items={mockItems} activeId="chat" onSelect={onSelect} />,
      );

      const filesButton = screen.getByLabelText("Files");
      fireEvent.keyDown(filesButton, { key: " " });
      expect(onSelect).toHaveBeenCalledWith("files");
    });
  });

  describe("disabled items", () => {
    it("renders disabled items with reduced opacity", () => {
      const itemsWithDisabled: ActivityItem[] = [
        { id: "test", icon: <MessageSquare />, label: "Test", disabled: true },
      ];
      render(
        <ActivityBar
          items={itemsWithDisabled}
          activeId="other"
          onSelect={() => {}}
        />,
      );

      expect(screen.getByLabelText("Test")).toHaveClass("opacity-50");
    });

    it("does not call onSelect for disabled items", () => {
      const onSelect = vi.fn();
      const itemsWithDisabled: ActivityItem[] = [
        { id: "test", icon: <MessageSquare />, label: "Test", disabled: true },
      ];
      render(
        <ActivityBar
          items={itemsWithDisabled}
          activeId="other"
          onSelect={onSelect}
        />,
      );

      fireEvent.click(screen.getByLabelText("Test"));
      expect(onSelect).not.toHaveBeenCalled();
    });
  });
});

describe("ActivityBarItem", () => {
  it("renders icon and handles click", () => {
    const onClick = vi.fn();
    render(
      <ActivityBarItem
        id="test"
        icon={<MessageSquare data-testid="icon" />}
        label="Test Item"
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByTestId("icon")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab"));
    expect(onClick).toHaveBeenCalled();
  });

  it("applies active styling when active", () => {
    render(
      <ActivityBarItem
        id="test"
        icon={<MessageSquare />}
        label="Test"
        isActive={true}
        onClick={() => {}}
      />,
    );

    expect(screen.getByRole("tab")).toHaveClass("bg-primary-100");
  });
});
