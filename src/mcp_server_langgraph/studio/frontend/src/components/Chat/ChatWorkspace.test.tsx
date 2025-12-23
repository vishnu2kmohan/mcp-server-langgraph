/**
 * ChatWorkspace Component Tests
 *
 * Tests for the DevTools-style dockable panel workspace.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ChatWorkspace } from "./ChatWorkspace";

describe("ChatWorkspace", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  const defaultProps = {
    sessionPanel: <div data-testid="session-panel">Sessions</div>,
    chatArea: <div data-testid="chat-area">Chat</div>,
    contextPanel: <div data-testid="context-panel">Context</div>,
  };

  describe("rendering", () => {
    it("renders all three panels", () => {
      render(<ChatWorkspace {...defaultProps} />);

      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
      expect(screen.getByTestId("chat-area")).toBeInTheDocument();
      expect(screen.getByTestId("context-panel")).toBeInTheDocument();
    });

    it("renders session panel content", () => {
      render(<ChatWorkspace {...defaultProps} />);
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });

    it("renders chat area content", () => {
      render(<ChatWorkspace {...defaultProps} />);
      expect(screen.getByText("Chat")).toBeInTheDocument();
    });

    it("renders context panel content", () => {
      render(<ChatWorkspace {...defaultProps} />);
      expect(screen.getByText("Context")).toBeInTheDocument();
    });
  });

  describe("optional header", () => {
    it("renders header when provided", () => {
      render(
        <ChatWorkspace
          {...defaultProps}
          header={<div data-testid="workspace-header">Header</div>}
        />,
      );

      expect(screen.getByTestId("workspace-header")).toBeInTheDocument();
      expect(screen.getByText("Header")).toBeInTheDocument();
    });

    it("does not render header when not provided", () => {
      render(<ChatWorkspace {...defaultProps} />);
      expect(screen.queryByTestId("workspace-header")).not.toBeInTheDocument();
    });
  });

  describe("panel configuration", () => {
    it("accepts custom persistence ID", () => {
      render(
        <ChatWorkspace {...defaultProps} persistenceId="custom-workspace" />,
      );

      // Component renders successfully with custom ID
      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
    });

    it("accepts custom panel sizes", () => {
      render(
        <ChatWorkspace
          {...defaultProps}
          sessionPanelDefaultSize={25}
          contextPanelDefaultSize={30}
        />,
      );

      // Component renders successfully with custom sizes
      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
      expect(screen.getByTestId("context-panel")).toBeInTheDocument();
    });

    it("accepts minimum panel size", () => {
      render(<ChatWorkspace {...defaultProps} sidePanelMinSize={15} />);

      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
    });
  });

  describe("collapsible panels", () => {
    it("session panel is collapsible by default", () => {
      render(<ChatWorkspace {...defaultProps} />);
      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
    });

    it("context panel is collapsible by default", () => {
      render(<ChatWorkspace {...defaultProps} />);
      expect(screen.getByTestId("context-panel")).toBeInTheDocument();
    });

    it("can disable session panel collapse", () => {
      render(
        <ChatWorkspace {...defaultProps} sessionPanelCollapsible={false} />,
      );
      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
    });

    it("can disable context panel collapse", () => {
      render(
        <ChatWorkspace {...defaultProps} contextPanelCollapsible={false} />,
      );
      expect(screen.getByTestId("context-panel")).toBeInTheDocument();
    });
  });

  describe("callbacks", () => {
    it("accepts onSessionPanelCollapse callback", () => {
      const onCollapse = vi.fn();
      render(
        <ChatWorkspace {...defaultProps} onSessionPanelCollapse={onCollapse} />,
      );
      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
    });

    it("accepts onSessionPanelExpand callback", () => {
      const onExpand = vi.fn();
      render(
        <ChatWorkspace {...defaultProps} onSessionPanelExpand={onExpand} />,
      );
      expect(screen.getByTestId("session-panel")).toBeInTheDocument();
    });

    it("accepts onContextPanelCollapse callback", () => {
      const onCollapse = vi.fn();
      render(
        <ChatWorkspace {...defaultProps} onContextPanelCollapse={onCollapse} />,
      );
      expect(screen.getByTestId("context-panel")).toBeInTheDocument();
    });

    it("accepts onContextPanelExpand callback", () => {
      const onExpand = vi.fn();
      render(
        <ChatWorkspace {...defaultProps} onContextPanelExpand={onExpand} />,
      );
      expect(screen.getByTestId("context-panel")).toBeInTheDocument();
    });
  });

  describe("complex content", () => {
    it("renders nested components in panels", () => {
      render(
        <ChatWorkspace
          sessionPanel={
            <div>
              <h2>Sessions List</h2>
              <ul>
                <li>Session 1</li>
                <li>Session 2</li>
              </ul>
            </div>
          }
          chatArea={
            <div>
              <header>Chat Header</header>
              <main>Messages</main>
              <footer>Input Form</footer>
            </div>
          }
          contextPanel={
            <div>
              <section>Tools</section>
              <section>Activity</section>
            </div>
          }
        />,
      );

      expect(screen.getByText("Sessions List")).toBeInTheDocument();
      expect(screen.getByText("Session 1")).toBeInTheDocument();
      expect(screen.getByText("Chat Header")).toBeInTheDocument();
      expect(screen.getByText("Messages")).toBeInTheDocument();
      expect(screen.getByText("Tools")).toBeInTheDocument();
      expect(screen.getByText("Activity")).toBeInTheDocument();
    });
  });
});
