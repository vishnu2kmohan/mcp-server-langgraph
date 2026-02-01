/**
 * WorkflowHeader Component
 *
 * Header component for the visual workflow builder with title, name input,
 * and action buttons (dark mode, settings, help).
 */

import { Sun, Moon, Settings, HelpCircle } from "lucide-react";

import { Button, Input } from "@/components/UI";

export interface WorkflowHeaderProps {
  workflowName: string;
  onNameChange: (name: string) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onOpenSettings: () => void;
  onOpenHelp: () => void;
}

export function WorkflowHeader({
  workflowName,
  onNameChange,
  isDarkMode,
  onToggleDarkMode,
  onOpenSettings,
  onOpenHelp,
}: WorkflowHeaderProps) {
  return (
    <header
      className={`px-6 py-4 border-b ${
        isDarkMode
          ? "bg-neutral-3 border-neutral-7"
          : "bg-neutral-1 border-neutral-5"
      }`}
    >
      <div className="flex items-center justify-between">
        <div>
          <h1
            className={`text-2xl font-bold ${
              isDarkMode ? "text-neutral-12" : "text-neutral-12"
            }`}
          >
            Visual Workflow Builder
          </h1>
          <p
            className={`text-sm ${
              isDarkMode ? "text-neutral-9" : "text-neutral-10"
            }`}
          >
            MCP Server with LangGraph - Build agents visually, export to code
          </p>
        </div>

        <div className="flex gap-2 items-center">
          <Input
            value={workflowName}
            onChange={(e) => onNameChange(e.target.value)}
            className={`px-3 py-2 border rounded-md ${
              isDarkMode ? "bg-neutral-3 border-neutral-6 text-neutral-12" : ""
            }`}
            placeholder="Workflow name"
          />
          <Button
            variant="primary"
            className="p-2 rounded-lg"
            onClick={onToggleDarkMode}
            title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
            aria-label={
              isDarkMode ? "Switch to light mode" : "Switch to dark mode"
            }
          >
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="p-2 rounded-lg"
            onClick={onOpenSettings}
            title="Settings"
            aria-label="Settings"
          >
            <Settings size={20} />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="p-2 rounded-lg"
            onClick={onOpenHelp}
            title="Help"
            aria-label="Help"
          >
            <HelpCircle size={20} />
          </Button>
        </div>
      </div>
    </header>
  );
}
