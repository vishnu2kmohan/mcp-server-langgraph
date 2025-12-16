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
  Info,
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
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg mb-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {icon && <span className="text-gray-500">{icon}</span>}
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {title}
        </span>
      </button>
      {isOpen && (
        <div className="p-3 pt-0 text-gray-700 dark:text-gray-300">
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
    bg: "bg-blue-50 dark:bg-blue-900/20",
    border: "border-blue-200 dark:border-blue-800",
    icon: <Info size={18} className="text-blue-600 dark:text-blue-400" />,
  },
  warning: {
    bg: "bg-yellow-50 dark:bg-yellow-900/20",
    border: "border-yellow-200 dark:border-yellow-800",
    icon: (
      <AlertTriangle
        size={18}
        className="text-yellow-600 dark:text-yellow-400"
      />
    ),
  },
  info: {
    bg: "bg-blue-50 dark:bg-blue-900/20",
    border: "border-blue-200 dark:border-blue-800",
    icon: <Info size={18} className="text-blue-600 dark:text-blue-400" />,
  },
  tip: {
    bg: "bg-green-50 dark:bg-green-900/20",
    border: "border-green-200 dark:border-green-800",
    icon: (
      <Lightbulb size={18} className="text-green-600 dark:text-green-400" />
    ),
  },
  check: {
    bg: "bg-green-50 dark:bg-green-900/20",
    border: "border-green-200 dark:border-green-800",
    icon: <Check size={18} className="text-green-600 dark:text-green-400" />,
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
            <div className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
              {title}
            </div>
          )}
          <div className="text-gray-700 dark:text-gray-300">{children}</div>
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
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors">
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-gray-500">{icon}</span>}
        <h4 className="font-semibold text-gray-900 dark:text-gray-100">
          {title}
        </h4>
      </div>
      {children && (
        <p className="text-sm text-gray-600 dark:text-gray-400">{children}</p>
      )}
    </div>
  );

  if (href) {
    return (
      <a href={href} className="block no-underline">
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
      className={`grid gap-4 my-4`}
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
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
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        {tabs.map((tab, index) => (
          <button
            key={index}
            onClick={() => setActiveTab(index)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === index
                ? "border-blue-500 text-blue-600 dark:text-blue-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            }`}
          >
            {tab.title}
          </button>
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
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
        <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
          •
        </span>
      </div>
      <div className="flex-1 pb-4 border-l-2 border-gray-200 dark:border-gray-700 pl-4 -ml-4 relative before:absolute before:left-0 before:top-4 before:w-4 before:h-0.5 before:bg-gray-200 dark:before:bg-gray-700">
        <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
          {title}
        </h4>
        <div className="text-gray-700 dark:text-gray-300">{children}</div>
      </div>
    </div>
  );
}

// ============================================================================
// MDX Component Registry
// ============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export const mdxComponents = {
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
  // Re-export for customization
  Info: () => <AlertCircle className="text-blue-500" />,
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
 * MDXArtifact renders MDX content with interactive components.
 * Currently renders as markdown - full MDX compilation requires async processing.
 */
export function MDXArtifact({
  data,
  title,
  components = {},
}: MDXArtifactProps) {
  // For now, display the MDX source with a note about interactive features
  // Full MDX compilation would require async rendering with @mdx-js/mdx
  return (
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
      {title && (
        <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-900">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {title}
          </h4>
        </div>
      )}
      <div className="p-4">
        <div className="mb-4 text-xs text-gray-500 flex items-center gap-2">
          <Info size={14} />
          <span>MDX document with interactive components</span>
          {Object.keys(components).length > 0 && (
            <span className="ml-2 px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 rounded">
              {Object.keys(components).length} custom components
            </span>
          )}
        </div>
        <pre className="text-sm font-mono bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto whitespace-pre-wrap">
          {data}
        </pre>
      </div>
    </div>
  );
}

export { Accordion, AccordionGroup, Callout, Note, Warning, Tip };
export { Card, CardGroup, Tabs, Tab, Steps, Step };
