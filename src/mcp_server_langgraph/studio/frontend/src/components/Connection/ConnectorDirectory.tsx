/**
 * ConnectorDirectory Component
 *
 * A grid layout component for displaying connector templates.
 * Uses Motion for staggered reveal animations per ADR-0102.
 *
 * @see ADR-0102 - Connections Page Redesign
 */

import { useState, useMemo } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { cn } from "@/utils/cn";
import {
  listContainerVariants,
  listItemVariants,
} from "@/design-system/micro-interactions";
import { Button } from "@/components/UI";
import { ConnectorCard } from "./ConnectorCard";
import type { ConnectionTemplateCamelCase } from "@/types/connectionTemplate";

// ============================================================================
// Types
// ============================================================================

export interface TemplateCategory {
  id: string;
  name: string;
  description: string;
}

export interface ConnectorDirectoryProps {
  /** Templates to display */
  templates: ConnectionTemplateCamelCase[];
  /** Available categories for filtering */
  categories?: TemplateCategory[];
  /** Callback when Connect is clicked on a template */
  onConnect: (template: ConnectionTemplateCamelCase) => void;
  /** IDs of templates that are already connected */
  connectedTemplateIds?: string[];
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export function ConnectorDirectory({
  templates,
  categories = [],
  onConnect,
  connectedTemplateIds = [],
  className,
}: ConnectorDirectoryProps) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const prefersReducedMotion = useReducedMotion();

  // Sort templates by popularity (descending) and filter by category
  const filteredAndSortedTemplates = useMemo(() => {
    let result = [...templates];

    // Filter by category if selected
    if (selectedCategory) {
      result = result.filter((t) => t.category === selectedCategory);
    }

    // Sort by popularity (higher first)
    result.sort((a, b) => b.popularity - a.popularity);

    return result;
  }, [templates, selectedCategory]);

  // Use reduced motion variants if user prefers
  const containerVariants = prefersReducedMotion
    ? undefined
    : listContainerVariants;
  const itemVariants = prefersReducedMotion ? undefined : listItemVariants;

  // Extract unique categories from templates if not provided
  const displayCategories = useMemo(() => {
    if (categories.length > 0) return categories;
    const uniqueCategories = [...new Set(templates.map((t) => t.category))];
    return uniqueCategories.map((id) => ({
      id,
      name: id.charAt(0).toUpperCase() + id.slice(1),
      description: "",
    }));
  }, [categories, templates]);

  return (
    <div className={cn("space-y-4", className)}>
      {/* Category Filter Chips */}
      {displayCategories.length > 0 && (
        <div
          className="flex flex-wrap gap-2"
          role="group"
          aria-label="Category filters"
        >
          <Button
            type="button"
            variant={selectedCategory === null ? "primary" : "secondary"}
            onClick={() => setSelectedCategory(null)}
            className={cn(
              "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
              selectedCategory === null
                ? "bg-primary-10 text-neutral-12"
                : "bg-neutral-2 text-neutral-11 hover:bg-neutral-4",
            )}
            aria-pressed={selectedCategory === null}
          >
            All
          </Button>
          {displayCategories.map((category) => (
            <Button
              key={category.id}
              type="button"
              variant={
                selectedCategory === category.id ? "primary" : "secondary"
              }
              onClick={() => setSelectedCategory(category.id)}
              className={cn(
                "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
                selectedCategory === category.id
                  ? "bg-primary-10 text-neutral-12"
                  : "bg-neutral-2 text-neutral-11 hover:bg-neutral-4",
              )}
              aria-pressed={selectedCategory === category.id}
            >
              {category.name}
            </Button>
          ))}
        </div>
      )}

      {/* Empty State */}
      {filteredAndSortedTemplates.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-2 text-4xl">🔌</div>
          <h3 className="text-lg font-medium text-neutral-12">
            No connectors available
          </h3>
          <p className="mt-1 text-sm text-neutral-11">
            {selectedCategory
              ? "No connectors found in this category. Try a different filter."
              : "No connector templates are currently available."}
          </p>
        </div>
      )}

      {/* Connector Grid */}
      {filteredAndSortedTemplates.length > 0 && (
        <motion.ul
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          role="list"
          aria-label="Connector templates"
        >
          <AnimatePresence mode="popLayout">
            {filteredAndSortedTemplates.map((template) => (
              <motion.li
                key={template.id}
                variants={itemVariants}
                layout
                exit={{ opacity: 0, scale: 0.95 }}
              >
                <ConnectorCard
                  template={template}
                  onConnect={onConnect}
                  isConnected={connectedTemplateIds.includes(template.id)}
                />
              </motion.li>
            ))}
          </AnimatePresence>
        </motion.ul>
      )}
    </div>
  );
}

export default ConnectorDirectory;
