/**
 * MDXArtifact Component
 *
 * Renders MDX content with interactive React components.
 * Supports Mintlify-style MDX documents with embedded JSX.
 *
 * Built-in Components:
 * - Accordion, AccordionGroup
 * - Callout (Note, Warning, Info, Tip)
 * - Card, CardGroup
 * - CodeGroup
 * - Tabs, Tab
 * - Steps, Step
 */

import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Info as InfoIcon,
  AlertTriangle,
  AlertCircle,
  Lightbulb,
  Check,
} from "lucide-react";

// ============================================================================
// Built-in MDX Components (Mintlify-compatible)
// ============================================================================

interface AccordionProps {
  title: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function Accordion({
  title,
  icon,
  defaultOpen = false,
  children,
}: AccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-neutral-5 rounded-lg mb-2">
      <Button
        variant="secondary"
        className="w-full flex p-3 text-left hover:bg-neutral-1"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {icon && (
          <span className="text-neutral-10">{icon}</span>
        )}
        <span className="font-medium text-neutral-12">
          {title}
        </span>
      </Button>
      {isOpen && (
        <div className="p-3 pt-0 text-neutral-11">
          {children}
        </div>
      )}
    </div>
  );
}

function AccordionGroup({ children }: { children: React.ReactNode }) {
  return <div className="my-4">{children}</div>;
}

type CalloutType = "note" | "warning" | "info" | "tip" | "check";

interface CalloutProps {
  type?: CalloutType;
  emoji?: string;
  title?: string;
  children: React.ReactNode;
}

const calloutStyles: Record<
  CalloutType,
  { bg: string; border: string; icon: React.ReactNode }
> = {
  note: {
    bg: "bg-primary-1 dark:bg-primary-a3",
    border: "border-primary-4 dark:border-primary-11",
    icon: (
      <InfoIcon size={18} className="text-primary-10 dark:text-primary-7" />
    ),
  },
  warning: {
    bg: "bg-warning-3 bg-warning-3",
    border: "border-warning-6 dark:border-warning-11",
    icon: (
      <AlertTriangle
        size={18}
        className="text-warning-9 dark:text-warning-9"
      />
    ),
  },
  info: {
    bg: "bg-primary-1 dark:bg-primary-a3",
    border: "border-primary-4 dark:border-primary-11",
    icon: (
      <InfoIcon size={18} className="text-primary-10 dark:text-primary-7" />
    ),
  },
  tip: {
    bg: "bg-success-1 dark:bg-success-a3",
    border: "border-success-4 dark:border-success-11",
    icon: (
      <Lightbulb size={18} className="text-success-10 dark:text-success-7" />
    ),
  },
  check: {
    bg: "bg-success-1 dark:bg-success-a3",
    border: "border-success-4 dark:border-success-11",
    icon: (
      <Check size={18} className="text-success-10 dark:text-success-7" />
    ),
  },
};

function Callout({ type = "note", emoji, title, children }: CalloutProps) {
  const style = calloutStyles[type];

  return (
    <div className={`my-4 p-4 rounded-lg border ${style.bg} ${style.border}`}>
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 mt-0.5">
          {emoji ? <span className="text-lg">{emoji}</span> : style.icon}
        </span>
        <div className="flex-1">
          {title && (
            <div className="font-semibold text-neutral-12 mb-1">
              {title}
            </div>
          )}
          <div className="text-neutral-11">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

// Shorthand callouts
function Note(props: Omit<CalloutProps, "type">) {
  return <Callout type="note" {...props} />;
}
function Warning(props: Omit<CalloutProps, "type">) {
  return <Callout type="warning" {...props} />;
}
function Tip(props: Omit<CalloutProps, "type">) {
  return <Callout type="tip" {...props} />;
}

interface CardProps {
  title: string;
  icon?: React.ReactNode;
  href?: string;
  children?: React.ReactNode;
}

function Card({ title, icon, href, children }: CardProps) {
  const content = (
    <div className="p-4 border border-neutral-5 rounded-lg hover:border-primary-9 dark:hover:border-primary-7 transition-colors">
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <span className="text-neutral-10">{icon}</span>
        )}
        <h4 className="font-semibold text-neutral-12">
          {title}
        </h4>
      </div>
      {children && (
        <p className="text-sm text-neutral-11">
          {children}
        </p>
      )}
    </div>
  );

  if (href) {
    return (
      <a href={href} className="block no-underline focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:ring-offset-2 rounded">
        {content}
      </a>
    );
  }

  return content;
}

function CardGroup({
  cols = 2,
  children,
}: {
  cols?: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className="grid-dynamic-cols gap-4 my-4"
      style={{ "--cols": cols } as React.CSSProperties}
    >
      {children}
    </div>
  );
}

interface TabsProps {
  children: React.ReactNode;
}

function Tabs({ children }: TabsProps) {
  const [activeTab, setActiveTab] = useState(0);

  // Extract tab titles and content from children
  const tabs = useMemo(() => {
    const tabArray: Array<{ title: string; content: React.ReactNode }> = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (children as any[])?.forEach((child: any) => {
      if (child?.props?.title) {
        tabArray.push({
          title: child.props.title,
          content: child.props.children,
        });
      }
    });
    return tabArray;
  }, [children]);

  return (
    <div className="my-4">
      <div className="flex border-b border-neutral-5">
        {tabs.map((tab, index) => (
          <Button
            variant="primary"
            className="px-4 py-2 text-sm border-b-2"
            key={index}
            onClick={() => setActiveTab(index)}>
            {tab.title}
          </Button>
        ))}
      </div>
      <div className="p-4">{tabs[activeTab]?.content}</div>
    </div>
  );
}

function Tab({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  // Tab content is extracted by parent Tabs component
  return <div data-title={title}>{children}</div>;
}

interface StepsProps {
  children: React.ReactNode;
}

function Steps({ children }: StepsProps) {
  return <div className="my-4 space-y-4">{children}</div>;
}

function Step({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-3 dark:bg-primary-12 flex items-center justify-center">
        <span className="text-sm font-semibold text-primary-10 dark:text-primary-7">
          •
        </span>
      </div>
      <div className="flex-1 pb-4 border-l-2 border-neutral-5 pl-4 -ml-4 relative before:absolute before:left-0 before:top-4 before:w-4 before:h-0.5 before:bg-neutral-3 dark:before:bg-neutral-4">
        <h4 className="font-semibold text-neutral-12 mb-1">
          {title}
        </h4>
        <div className="text-neutral-11">{children}</div>
      </div>
    </div>
  );
}

// ============================================================================
// Extended MDX Components (Mintlify-compatible)
// ============================================================================

function Info(props: Omit<CalloutProps, "type">) {
  return <Callout type="info" {...props} />;
}

function CheckCallout(props: Omit<CalloutProps, "type">) {
  return <Callout type="check" {...props} />;
}

interface CodeGroupProps {
  children: React.ReactNode;
}

function CodeGroup({ children }: CodeGroupProps) {
  // CodeGroup renders children in a tabbed code block view
  return (
    <div className="my-4 border border-neutral-5 rounded-lg overflow-hidden">
      <div className="bg-neutral-2 px-4 py-2 text-sm font-mono text-neutral-11">
        Code Examples
      </div>
      <div className="p-4 bg-neutral-1 font-mono text-sm overflow-x-auto">
        {children}
      </div>
    </div>
  );
}

interface FrameProps {
  caption?: string;
  children: React.ReactNode;
}

function Frame({ caption, children }: FrameProps) {
  return (
    <figure className="my-4">
      <div className="border border-neutral-5 rounded-lg overflow-hidden">
        {children}
      </div>
      {caption && (
        <figcaption className="mt-2 text-sm text-center text-neutral-10">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}

interface ExpandableProps {
  title: string;
  children: React.ReactNode;
}

function Expandable({ title, children }: ExpandableProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="my-4">
      <Button
        variant="primary"
        className="flex text-primary-10 dark:text-primary-7 hover:underline"
        onClick={() => setIsOpen(!isOpen)}>
        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <span>{title}</span>
      </Button>
      {isOpen && (
        <div className="mt-2 pl-6 text-neutral-11">
          {children}
        </div>
      )}
    </div>
  );
}

interface IconProps {
  icon: string;
  size?: number;
  color?: string;
}

function Icon({ icon, size = 16, color }: IconProps) {
  // Simple icon placeholder - in a full implementation, would map to actual icons
  return (
    <span
      className={`inline-flex items-center justify-center ${color || "text-neutral-10"}`}
      style={{ width: size, height: size }}
      aria-label={icon}
    >
      {icon === "check" && <Check size={size} />}
      {icon === "info" && <AlertCircle size={size} />}
      {icon === "warning" && <AlertTriangle size={size} />}
      {icon === "lightbulb" && <Lightbulb size={size} />}
      {!["check", "info", "warning", "lightbulb"].includes(icon) && (
        <span className="text-xs">•</span>
      )}
    </span>
  );
}

interface ResponseFieldProps {
  name: string;
  type?: string;
  required?: boolean;
  children?: React.ReactNode;
}

function ResponseField({ name, type, required, children }: ResponseFieldProps) {
  return (
    <div className="my-4 p-4 border border-neutral-5 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <code className="px-2 py-0.5 bg-neutral-2 text-primary-10 dark:text-primary-7 rounded">
          {name}
        </code>
        {type && (
          <span className="text-sm text-neutral-10">
            {type}
          </span>
        )}
        {required && (
          <span className="px-2 py-0.5 text-xs bg-error-3 bg-error-4 text-error-10 dark:text-error-7 rounded">
            required
          </span>
        )}
      </div>
      {children && (
        <div className="text-sm text-neutral-11">
          {children}
        </div>
      )}
    </div>
  );
}

interface ParamFieldProps {
  path?: string;
  query?: string;
  body?: string;
  type?: string;
  required?: boolean;
  children?: React.ReactNode;
}

function ParamField({
  path,
  query,
  body,
  type,
  required,
  children,
}: ParamFieldProps) {
  const name = path || query || body || "param";
  const paramType = path ? "path" : query ? "query" : body ? "body" : "param";

  return (
    <div className="my-4 p-4 border border-neutral-5 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <code className="px-2 py-0.5 bg-neutral-2 text-primary-10 dark:text-primary-7 rounded">
          {name}
        </code>
        <span className="px-2 py-0.5 text-xs bg-neutral-2 text-neutral-11 rounded">
          {paramType}
        </span>
        {type && (
          <span className="text-sm text-neutral-10">
            {type}
          </span>
        )}
        {required && (
          <span className="px-2 py-0.5 text-xs bg-error-3 bg-error-4 text-error-10 dark:text-error-7 rounded">
            required
          </span>
        )}
      </div>
      {children && (
        <div className="text-sm text-neutral-11">
          {children}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MDX Component Registry
// ============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export const mdxComponents = {
  // Core
  Accordion,
  AccordionGroup,
  Callout,
  Note,
  Warning,
  Tip,
  Info,
  Check: CheckCallout,
  Card,
  CardGroup,
  Tabs,
  Tab,
  Steps,
  Step,
  // Extended
  CodeGroup,
  Frame,
  Expandable,
  Icon,
  ResponseField,
  ParamField,
};

// ============================================================================
// MDX Parser Integration
// ============================================================================

import {
  parseMDXContent,
  hasMDXComponents,
  type MDXParsedNode,
} from "../../utils/mdxParser";

import { Button } from "@/components/UI";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyComponent = React.ComponentType<any>;

// Component map for rendering parsed MDX
const COMPONENT_MAP: Record<string, AnyComponent> = {
  // Core
  Callout,
  Note,
  Warning,
  Tip,
  Info,
  Check: CheckCallout,
  Accordion,
  AccordionGroup,
  Card,
  CardGroup,
  Tabs,
  Tab,
  Steps,
  Step,
  // Extended
  CodeGroup,
  Frame,
  Expandable,
  Icon,
  ResponseField,
  ParamField,
};

// ============================================================================
// MDXArtifact Component
// ============================================================================

export interface MDXArtifactProps {
  data: string;
  title?: string;
  components?: Record<string, React.ComponentType>;
}

/**
 * Render a single parsed MDX node
 */
function renderNode(
  node: MDXParsedNode,
  index: number,
  customComponents: Record<string, AnyComponent>,
): React.ReactNode {
  if (node.type === "text") {
    // Render text as markdown prose
    return (
      <div
        key={`text-${index}`}
        className="prose dark:prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: node.content || "" }}
      />
    );
  }

  if (node.type === "component" && node.component) {
    const Component =
      customComponents[node.component] || COMPONENT_MAP[node.component];
    if (!Component) {
      // Unknown component - render as code block
      return (
        <pre
          key={`unknown-${index}`}
          className="text-sm font-mono bg-neutral-2 p-3 rounded overflow-x-auto"
        >
          {`<${node.component}>...</${node.component}>`}
        </pre>
      );
    }

    // Check if children contain nested components
    const hasNestedComponents =
      node.children && hasMDXComponents(node.children);

    if (hasNestedComponents) {
      // Recursively parse and render children
      const childNodes = parseMDXContent(node.children || "");
      return (
        <Component key={`component-${index}`} {...node.props}>
          {childNodes.map((childNode, childIndex) =>
            renderNode(childNode, childIndex, customComponents),
          )}
        </Component>
      );
    }

    // Render component with text children
    return (
      <Component key={`component-${index}`} {...node.props}>
        {node.children}
      </Component>
    );
  }

  return null;
}

/**
 * MDXArtifact renders MDX content with interactive components.
 * Uses lightweight parser to extract and render known components.
 */
export function MDXArtifact({
  data,
  title,
  components = {},
}: MDXArtifactProps) {
  // Parse MDX content into nodes
  const nodes = useMemo(() => parseMDXContent(data), [data]);

  // Check if content has any MDX components
  const hasComponents = useMemo(() => hasMDXComponents(data), [data]);

  // Merge custom components with built-in components
  const mergedComponents = useMemo(
    () => ({ ...COMPONENT_MAP, ...components }),
    [components],
  );

  // If no MDX components found, render as plain markdown
  if (!hasComponents) {
    return (
      <div
        data-testid="mdx-artifact"
        className="bg-neutral-1 rounded-lg overflow-hidden border border-neutral-5"
      >
        {title && (
          <div className="px-4 py-2 border-b border-neutral-5 bg-neutral-2">
            <h4 className="text-sm font-medium text-neutral-11">
              {title}
            </h4>
          </div>
        )}
        <div className="p-4 prose dark:prose-invert max-w-none">
          <div dangerouslySetInnerHTML={{ __html: data }} />
        </div>
      </div>
    );
  }

  // Render MDX with interactive components
  return (
    <div
      data-testid="mdx-artifact"
      className="bg-neutral-1 rounded-lg overflow-hidden border border-neutral-5"
    >
      {title && (
        <div className="px-4 py-2 border-b border-neutral-5 bg-neutral-2 flex items-center gap-2">
          <InfoIcon size={14} className="text-primary-9" />
          <h4 className="text-sm font-medium text-neutral-11">
            {title}
          </h4>
          <span className="ml-auto px-2 py-0.5 text-xs bg-primary-3 bg-primary-4 text-primary-10 dark:text-primary-7 rounded">
            Interactive
          </span>
        </div>
      )}
      <div className="p-4 space-y-4">
        {nodes.map((node, index) => renderNode(node, index, mergedComponents))}
      </div>
    </div>
  );
}

export { Accordion, AccordionGroup, Callout, Note, Warning, Tip };
export { Card, CardGroup, Tabs, Tab, Steps, Step };
