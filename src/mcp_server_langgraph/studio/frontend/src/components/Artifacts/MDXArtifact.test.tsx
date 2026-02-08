/**
 * MDXArtifact Tests
 *
 * Tests for MDX content rendering with interactive components.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  MDXArtifact,
  Accordion,
  AccordionGroup,
  Callout,
  Note,
  Warning,
  Tip,
  Card,
  CardGroup,
  Tabs,
  Tab,
  Steps,
  Step,
  mdxComponents,
} from "./MDXArtifact";

import { TestProvider } from "@/test-utils";

describe("MDXArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Main Component", () => {
    it("should render MDX content", () => {
      render(
        <TestProvider>
          <MDXArtifact data="# Hello World" />
        </TestProvider>,
      );
      expect(screen.getByText("# Hello World")).toBeInTheDocument();
    });

    it("should render with title when provided", () => {
      render(
        <TestProvider>
          <MDXArtifact data="content" title="Test Document" />
        </TestProvider>,
      );
      expect(screen.getByText("Test Document")).toBeInTheDocument();
    });

    it("should render without title when not provided", () => {
      render(
        <TestProvider>
          <MDXArtifact data="content" />
        </TestProvider>,
      );
      expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    });

    it("should accept custom components prop", () => {
      const customComponents = {
        CustomButton: () => <button>Custom</button>,
        CustomAlert: () => <div>Alert</div>,
      };
      // Custom components are merged with built-in components for rendering
      // The component renders successfully when custom components are provided
      render(
        <TestProvider>
          <MDXArtifact data="content" components={customComponents} />
        </TestProvider>,
      );
      expect(screen.getByTestId("mdx-artifact")).toBeInTheDocument();
    });

    it("should not show components badge when no custom components", () => {
      render(
        <TestProvider>
          <MDXArtifact data="content" />
        </TestProvider>,
      );
      expect(screen.queryByText(/custom components/)).not.toBeInTheDocument();
    });
  });

  describe("Accordion Component", () => {
    it("should render collapsed by default", () => {
      render(
        <TestProvider>
          <Accordion title="Click me">
            <p>Hidden content</p>
          </Accordion>
        </TestProvider>,
      );
      expect(screen.getByText("Click me")).toBeInTheDocument();
      expect(screen.queryByText("Hidden content")).not.toBeInTheDocument();
    });

    it("should expand when clicked", () => {
      render(
        <TestProvider>
          <Accordion title="Click me">
            <p>Hidden content</p>
          </Accordion>
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button"));
      expect(screen.getByText("Hidden content")).toBeInTheDocument();
    });

    it("should collapse when clicked again", () => {
      render(
        <TestProvider>
          <Accordion title="Click me">
            <p>Hidden content</p>
          </Accordion>
        </TestProvider>,
      );
      const button = screen.getByRole("button");
      fireEvent.click(button);
      expect(screen.getByText("Hidden content")).toBeInTheDocument();
      fireEvent.click(button);
      expect(screen.queryByText("Hidden content")).not.toBeInTheDocument();
    });

    it("should render open when defaultOpen is true", () => {
      render(
        <TestProvider>
          <Accordion title="Click me" defaultOpen>
            <p>Visible content</p>
          </Accordion>
        </TestProvider>,
      );
      expect(screen.getByText("Visible content")).toBeInTheDocument();
    });

    it("should render icon when provided", () => {
      render(
        <TestProvider>
          <Accordion title="Click me" icon={<span data-testid="icon">🎉</span>}>
            <p>Content</p>
          </Accordion>
        </TestProvider>,
      );
      expect(screen.getByTestId("icon")).toBeInTheDocument();
    });
  });

  describe("AccordionGroup Component", () => {
    it("should render children", () => {
      render(
        <TestProvider>
          <AccordionGroup>
            <Accordion title="First">Content 1</Accordion>
            <Accordion title="Second">Content 2</Accordion>
          </AccordionGroup>
        </TestProvider>,
      );
      expect(screen.getByText("First")).toBeInTheDocument();
      expect(screen.getByText("Second")).toBeInTheDocument();
    });
  });

  describe("Callout Component", () => {
    it("should render note type by default", () => {
      render(
        <TestProvider>
          <Callout>This is a note</Callout>
        </TestProvider>,
      );
      expect(screen.getByText("This is a note")).toBeInTheDocument();
    });

    it("should render with title when provided", () => {
      render(
        <TestProvider>
          <Callout title="Important">Content here</Callout>
        </TestProvider>,
      );
      expect(screen.getByText("Important")).toBeInTheDocument();
      expect(screen.getByText("Content here")).toBeInTheDocument();
    });

    it("should render with emoji when provided", () => {
      render(
        <TestProvider>
          <Callout emoji="🚀">Rocket content</Callout>
        </TestProvider>,
      );
      expect(screen.getByText("🚀")).toBeInTheDocument();
    });

    it("should render warning type", () => {
      render(
        <TestProvider>
          <Callout type="warning">Warning message</Callout>
        </TestProvider>,
      );
      expect(screen.getByText("Warning message")).toBeInTheDocument();
    });

    it("should render tip type", () => {
      render(
        <TestProvider>
          <Callout type="tip">Helpful tip</Callout>
        </TestProvider>,
      );
      expect(screen.getByText("Helpful tip")).toBeInTheDocument();
    });

    it("should render info type", () => {
      render(
        <TestProvider>
          <Callout type="info">Info message</Callout>
        </TestProvider>,
      );
      expect(screen.getByText("Info message")).toBeInTheDocument();
    });

    it("should render check type", () => {
      render(
        <TestProvider>
          <Callout type="check">Success message</Callout>
        </TestProvider>,
      );
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });
  });

  describe("Shorthand Callouts", () => {
    it("should render Note component", () => {
      render(
        <TestProvider>
          <Note>Note content</Note>
        </TestProvider>,
      );
      expect(screen.getByText("Note content")).toBeInTheDocument();
    });

    it("should render Warning component", () => {
      render(
        <TestProvider>
          <Warning>Warning content</Warning>
        </TestProvider>,
      );
      expect(screen.getByText("Warning content")).toBeInTheDocument();
    });

    it("should render Tip component", () => {
      render(
        <TestProvider>
          <Tip>Tip content</Tip>
        </TestProvider>,
      );
      expect(screen.getByText("Tip content")).toBeInTheDocument();
    });
  });

  describe("Card Component", () => {
    it("should render card with title", () => {
      render(
        <TestProvider>
          <Card title="Card Title">Card content</Card>
        </TestProvider>,
      );
      expect(screen.getByText("Card Title")).toBeInTheDocument();
      expect(screen.getByText("Card content")).toBeInTheDocument();
    });

    it("should render card without children", () => {
      render(
        <TestProvider>
          <Card title="Title Only" />
        </TestProvider>,
      );
      expect(screen.getByText("Title Only")).toBeInTheDocument();
    });

    it("should render card with icon", () => {
      render(
        <TestProvider>
          <Card title="Card" icon={<span data-testid="card-icon">📦</span>}>
            Content
          </Card>
        </TestProvider>,
      );
      expect(screen.getByTestId("card-icon")).toBeInTheDocument();
    });

    it("should render as link when href provided", () => {
      render(
        <TestProvider>
          <Card title="Link Card" href="/some-path">
            Clickable
          </Card>
        </TestProvider>,
      );
      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/some-path");
    });

    it("should not render as link when no href", () => {
      render(
        <TestProvider>
          <Card title="No Link">Not clickable</Card>
        </TestProvider>,
      );
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
    });
  });

  describe("CardGroup Component", () => {
    it("should render cards in grid", () => {
      render(
        <TestProvider>
          <CardGroup>
            <Card title="Card 1">Content 1</Card>
            <Card title="Card 2">Content 2</Card>
          </CardGroup>
        </TestProvider>,
      );
      expect(screen.getByText("Card 1")).toBeInTheDocument();
      expect(screen.getByText("Card 2")).toBeInTheDocument();
    });

    it("should use custom column count", () => {
      const { container } = render(
        <TestProvider>
          <CardGroup cols={3}>
            <Card title="Card 1">Content</Card>
          </CardGroup>
        </TestProvider>,
      );
      const grid = container.querySelector('[style*="repeat(3"]');
      expect(grid).toBeInTheDocument();
    });
  });

  describe("Tabs Component", () => {
    it("should render first tab content by default", () => {
      render(
        <TestProvider>
          <Tabs>
            <Tab title="First">First content</Tab>
            <Tab title="Second">Second content</Tab>
          </Tabs>
        </TestProvider>,
      );
      expect(screen.getByText("First content")).toBeInTheDocument();
    });

    it("should switch tabs when clicked", () => {
      render(
        <TestProvider>
          <Tabs>
            <Tab title="First">First content</Tab>
            <Tab title="Second">Second content</Tab>
          </Tabs>
        </TestProvider>,
      );
      fireEvent.click(screen.getByText("Second"));
      expect(screen.getByText("Second content")).toBeInTheDocument();
    });

    it("should render tab buttons", () => {
      render(
        <TestProvider>
          <Tabs>
            <Tab title="Tab A">Content A</Tab>
            <Tab title="Tab B">Content B</Tab>
          </Tabs>
        </TestProvider>,
      );
      expect(screen.getByText("Tab A")).toBeInTheDocument();
      expect(screen.getByText("Tab B")).toBeInTheDocument();
    });

    it("should handle empty tabs gracefully", () => {
      render(
        <TestProvider>
          <Tabs>{null}</Tabs>
        </TestProvider>,
      );
      // Should not crash
      expect(document.body).toBeInTheDocument();
    });
  });

  describe("Steps Component", () => {
    it("should render steps", () => {
      render(
        <TestProvider>
          <Steps>
            <Step title="Step 1">First step content</Step>
            <Step title="Step 2">Second step content</Step>
          </Steps>
        </TestProvider>,
      );
      expect(screen.getByText("Step 1")).toBeInTheDocument();
      expect(screen.getByText("First step content")).toBeInTheDocument();
      expect(screen.getByText("Step 2")).toBeInTheDocument();
    });
  });

  describe("Extended Components", () => {
    // Access extended components from mdxComponents registry
    const Info = mdxComponents.Info;
    const Check = mdxComponents.Check;
    const CodeGroup = mdxComponents.CodeGroup;
    const Frame = mdxComponents.Frame;
    const Expandable = mdxComponents.Expandable;
    const Icon = mdxComponents.Icon;
    const ResponseField = mdxComponents.ResponseField;
    const ParamField = mdxComponents.ParamField;

    describe("Info Component", () => {
      it("should render info callout", () => {
        render(
          <TestProvider>
            <Info>Information message</Info>
          </TestProvider>,
        );
        expect(screen.getByText("Information message")).toBeInTheDocument();
      });

      it("should render with title", () => {
        render(
          <TestProvider>
            <Info title="FYI">Details here</Info>
          </TestProvider>,
        );
        expect(screen.getByText("FYI")).toBeInTheDocument();
        expect(screen.getByText("Details here")).toBeInTheDocument();
      });
    });

    describe("Check Component", () => {
      it("should render check/success callout", () => {
        render(
          <TestProvider>
            <Check>Task completed successfully!</Check>
          </TestProvider>,
        );
        expect(
          screen.getByText("Task completed successfully!"),
        ).toBeInTheDocument();
      });

      it("should render with title", () => {
        render(
          <TestProvider>
            <Check title="Done">All tests passed</Check>
          </TestProvider>,
        );
        expect(screen.getByText("Done")).toBeInTheDocument();
        expect(screen.getByText("All tests passed")).toBeInTheDocument();
      });
    });

    describe("CodeGroup Component", () => {
      it("should render code group container", () => {
        render(
          <TestProvider>
            <CodeGroup>
              <pre>python code</pre>
              <pre>javascript code</pre>
            </CodeGroup>
          </TestProvider>,
        );
        expect(screen.getByText("Code Examples")).toBeInTheDocument();
        expect(screen.getByText("python code")).toBeInTheDocument();
        expect(screen.getByText("javascript code")).toBeInTheDocument();
      });
    });

    describe("Frame Component", () => {
      it("should render frame without caption", () => {
        render(
          <TestProvider>
            <Frame>
              <img src="test.png" alt="Test" />
            </Frame>
          </TestProvider>,
        );
        expect(screen.getByRole("img")).toBeInTheDocument();
      });

      it("should render frame with caption", () => {
        render(
          <TestProvider>
            <Frame caption="Example image">
              <img src="test.png" alt="Test" />
            </Frame>
          </TestProvider>,
        );
        expect(screen.getByText("Example image")).toBeInTheDocument();
      });
    });

    describe("Expandable Component", () => {
      it("should render collapsed by default", () => {
        render(
          <TestProvider>
            <Expandable title="Show more">
              <p>Hidden details</p>
            </Expandable>
          </TestProvider>,
        );
        expect(screen.getByText("Show more")).toBeInTheDocument();
        expect(screen.queryByText("Hidden details")).not.toBeInTheDocument();
      });

      it("should expand when clicked", () => {
        render(
          <TestProvider>
            <Expandable title="Show more">
              <p>Hidden details</p>
            </Expandable>
          </TestProvider>,
        );
        fireEvent.click(screen.getByRole("button"));
        expect(screen.getByText("Hidden details")).toBeInTheDocument();
      });

      it("should collapse when clicked again", () => {
        render(
          <TestProvider>
            <Expandable title="Show more">
              <p>Hidden details</p>
            </Expandable>
          </TestProvider>,
        );
        const button = screen.getByRole("button");
        fireEvent.click(button);
        expect(screen.getByText("Hidden details")).toBeInTheDocument();
        fireEvent.click(button);
        expect(screen.queryByText("Hidden details")).not.toBeInTheDocument();
      });
    });

    describe("Icon Component", () => {
      it("should render check icon", () => {
        render(
          <TestProvider>
            <Icon icon="check" />
          </TestProvider>,
        );
        // Icon should be rendered with aria-label
        expect(screen.getByLabelText("check")).toBeInTheDocument();
      });

      it("should render info icon", () => {
        render(
          <TestProvider>
            <Icon icon="info" />
          </TestProvider>,
        );
        expect(screen.getByLabelText("info")).toBeInTheDocument();
      });

      it("should render warning icon", () => {
        render(
          <TestProvider>
            <Icon icon="warning" />
          </TestProvider>,
        );
        expect(screen.getByLabelText("warning")).toBeInTheDocument();
      });

      it("should render lightbulb icon", () => {
        render(
          <TestProvider>
            <Icon icon="lightbulb" />
          </TestProvider>,
        );
        expect(screen.getByLabelText("lightbulb")).toBeInTheDocument();
      });

      it("should render fallback for unknown icons", () => {
        render(
          <TestProvider>
            <Icon icon="unknown" />
          </TestProvider>,
        );
        expect(screen.getByLabelText("unknown")).toBeInTheDocument();
      });

      it("should accept size prop", () => {
        render(
          <TestProvider>
            <Icon icon="check" size={24} />
          </TestProvider>,
        );
        const iconElement = screen.getByLabelText("check");
        expect(iconElement).toHaveStyle({ width: "24px", height: "24px" });
      });
    });

    describe("ResponseField Component", () => {
      it("should render response field with name", () => {
        render(
          <TestProvider>
            <ResponseField name="id">The unique identifier</ResponseField>
          </TestProvider>,
        );
        expect(screen.getByText("id")).toBeInTheDocument();
        expect(screen.getByText("The unique identifier")).toBeInTheDocument();
      });

      it("should render with type", () => {
        render(
          <TestProvider>
            <ResponseField name="count" type="number">
              The count value
            </ResponseField>
          </TestProvider>,
        );
        expect(screen.getByText("count")).toBeInTheDocument();
        expect(screen.getByText("number")).toBeInTheDocument();
      });

      it("should show required badge when required", () => {
        render(
          <TestProvider>
            <ResponseField name="email" required>
              User email address
            </ResponseField>
          </TestProvider>,
        );
        expect(screen.getByText("required")).toBeInTheDocument();
      });

      it("should render without children", () => {
        render(
          <TestProvider>
            <ResponseField name="data" type="object" />
          </TestProvider>,
        );
        expect(screen.getByText("data")).toBeInTheDocument();
        expect(screen.getByText("object")).toBeInTheDocument();
      });
    });

    describe("ParamField Component", () => {
      it("should render param field with path parameter", () => {
        render(
          <TestProvider>
            <ParamField path="user_id">The user ID to fetch</ParamField>
          </TestProvider>,
        );
        expect(screen.getByText("user_id")).toBeInTheDocument();
        expect(screen.getByText("path")).toBeInTheDocument();
        expect(screen.getByText("The user ID to fetch")).toBeInTheDocument();
      });

      it("should render query parameter", () => {
        render(
          <TestProvider>
            <ParamField query="limit" type="integer">
              Maximum results to return
            </ParamField>
          </TestProvider>,
        );
        expect(screen.getByText("limit")).toBeInTheDocument();
        expect(screen.getByText("query")).toBeInTheDocument();
        expect(screen.getByText("integer")).toBeInTheDocument();
      });

      it("should render body parameter", () => {
        render(
          <TestProvider>
            <ParamField body="payload" type="object">
              Request body data
            </ParamField>
          </TestProvider>,
        );
        expect(screen.getByText("payload")).toBeInTheDocument();
        expect(screen.getByText("body")).toBeInTheDocument();
      });

      it("should show required badge when required", () => {
        render(
          <TestProvider>
            <ParamField path="id" required>
              Required parameter
            </ParamField>
          </TestProvider>,
        );
        expect(screen.getByText("required")).toBeInTheDocument();
      });

      it("should render without children", () => {
        render(
          <TestProvider>
            <ParamField query="page" type="integer" />
          </TestProvider>,
        );
        expect(screen.getByText("page")).toBeInTheDocument();
        expect(screen.getByText("query")).toBeInTheDocument();
      });
    });
  });

  describe("Component Registry", () => {
    it("should export all core components", () => {
      expect(mdxComponents.Accordion).toBeDefined();
      expect(mdxComponents.AccordionGroup).toBeDefined();
      expect(mdxComponents.Callout).toBeDefined();
      expect(mdxComponents.Note).toBeDefined();
      expect(mdxComponents.Warning).toBeDefined();
      expect(mdxComponents.Tip).toBeDefined();
      expect(mdxComponents.Card).toBeDefined();
      expect(mdxComponents.CardGroup).toBeDefined();
      expect(mdxComponents.Tabs).toBeDefined();
      expect(mdxComponents.Tab).toBeDefined();
      expect(mdxComponents.Steps).toBeDefined();
      expect(mdxComponents.Step).toBeDefined();
    });

    it("should export all extended components", () => {
      expect(mdxComponents.Info).toBeDefined();
      expect(mdxComponents.Check).toBeDefined();
      expect(mdxComponents.CodeGroup).toBeDefined();
      expect(mdxComponents.Frame).toBeDefined();
      expect(mdxComponents.Expandable).toBeDefined();
      expect(mdxComponents.Icon).toBeDefined();
      expect(mdxComponents.ResponseField).toBeDefined();
      expect(mdxComponents.ParamField).toBeDefined();
    });

    it("should have 20 total components in registry", () => {
      // Core: Accordion, AccordionGroup, Callout, Note, Warning, Tip, Info, Check, Card, CardGroup, Tabs, Tab, Steps, Step (14)
      // Extended: CodeGroup, Frame, Expandable, Icon, ResponseField, ParamField (6)
      expect(Object.keys(mdxComponents)).toHaveLength(20);
    });
  });
});
