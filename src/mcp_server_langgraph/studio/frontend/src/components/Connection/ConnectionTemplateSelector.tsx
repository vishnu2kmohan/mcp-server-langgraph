/**
 * ConnectionTemplateSelector Component
 *
 * Allows users to select from pre-configured MCP server templates.
 * Includes category filtering, search, and custom connection option.
 */

import { useState, useEffect, useCallback } from "react";
import { authenticatedFetch } from "../../utils/authenticatedFetch";
import {
  transformSnakeToCamel,
  type SnakeToCamelCaseDeep,
} from "../../api/transforms";

import { Button, Input } from "@/components/UI";

// ============================================================================
// Types
// ============================================================================

/** Config field for template-specific settings */
interface ConfigField {
  name: string;
  label: string;
  type: "text" | "password" | "url" | "textarea";
  required: boolean;
  placeholder?: string;
  description?: string;
  default?: string;
}

/** Raw API response type (snake_case from backend) */
interface ConnectionTemplateRaw {
  id: string;
  name: string;
  description: string;
  icon: string;
  auth_type: "none" | "api_key" | "oauth2";
  default_url: string;
  category: string;
  oauth2_scopes?: string[];
  config_fields?: ConfigField[];
}

/**
 * Frontend-friendly connection template type (camelCase).
 * Derived from ConnectionTemplateRaw via ADR-0091 Phase 6 type transformation.
 */
export type ConnectionTemplate = SnakeToCamelCaseDeep<ConnectionTemplateRaw>;

interface TemplateCategory {
  id: string;
  name: string;
  description: string;
}

interface ConnectionTemplateSelectorProps {
  onSelect: (template: ConnectionTemplate) => void;
  onCustom?: () => void;
  showCustomOption?: boolean;
}

// ============================================================================
// Icon Mapping
// ============================================================================

const getIconEmoji = (icon: string): string => {
  const iconMap: Record<string, string> = {
    github: "🐙",
    gitlab: "🦊",
    slack: "💬",
    discord: "🎮",
    notion: "📝",
    jira: "📋",
    linear: "📐",
    folder: "📁",
    database: "🗄️",
    key: "🔑",
    lock: "🔒",
    custom: "⚙️",
  };
  return iconMap[icon] || "🔌";
};

// ============================================================================
// Component
// ============================================================================

export function ConnectionTemplateSelector({
  onSelect,
  onCustom,
  showCustomOption = false,
}: ConnectionTemplateSelectorProps) {
  const [templates, setTemplates] = useState<ConnectionTemplate[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch templates and categories
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Build URL with filters
      const params = new URLSearchParams();
      if (selectedCategory) {
        params.append("category", selectedCategory);
      }
      if (searchQuery) {
        params.append("search", searchQuery);
      }

      const templateUrl = `/api/v1/connection-templates${params.toString() ? `?${params.toString()}` : ""}`;

      const [templatesRes, categoriesRes] = await Promise.all([
        authenticatedFetch(templateUrl),
        authenticatedFetch("/api/v1/connection-templates/categories"),
      ]);

      if (!templatesRes.ok || !categoriesRes.ok) {
        throw new Error("Failed to fetch templates");
      }

      const templatesData = await templatesRes.json();
      const categoriesData = await categoriesRes.json();

      // Transform snake_case API response to camelCase (ADR-0091 Phase 6)
      const transformedTemplates = (templatesData.templates || []).map(
        (t: ConnectionTemplateRaw) => transformSnakeToCamel(t),
      );
      setTemplates(transformedTemplates);
      setCategories(categoriesData.categories || []);
    } catch (err) {
      setError("Failed to load templates. Please try again.");
      console.error("Error fetching templates:", err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, searchQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle template selection
  const handleSelectTemplate = (template: ConnectionTemplate) => {
    setSelectedTemplateId(template.id);
    onSelect(template);
  };

  // Handle category filter
  const handleCategoryChange = (categoryId: string | null) => {
    setSelectedCategory(categoryId);
  };

  // Handle search
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  // Handle retry
  const handleRetry = () => {
    fetchData();
  };

  // Get auth type badge Tailwind classes
  const getAuthTypeBadgeClasses = (authType: string): string => {
    switch (authType) {
      case "oauth2":
        return "bg-primary-3 text-primary-11";
      case "api_key":
        return "bg-warning-3 text-warning-11";
      default:
        return "bg-success-3 text-success-11";
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-2xl font-semibold mb-4 text-neutral-12">
        Choose a Template
      </h2>
      {/* Search */}
      <div className="mb-4">
        <Input
          className="w-full"
          placeholder="Search templates..."
          value={searchQuery}
          onChange={handleSearchChange}
        />
      </div>
      {/* Category Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <Button
          variant={selectedCategory === null ? "primary" : "outline"}
          size="sm"
          className="rounded-full"
          onClick={() => handleCategoryChange(null)}
        >
          All
        </Button>
        {categories.map((category) => (
          <Button
            variant={selectedCategory === category.id ? "primary" : "outline"}
            size="sm"
            className="rounded-full"
            key={category.id}
            onClick={() => handleCategoryChange(category.id)}
          >
            {category.name}
          </Button>
        ))}
      </div>
      {/* Loading State */}
      {isLoading && (
        <div
          className="flex flex-col items-center justify-center p-12 text-neutral-10"
          data-testid="loading-templates"
        >
          <div className="w-8 h-8 border-[3px] border-neutral-5 border-t-primary-9 rounded-full animate-spin mb-4" />
          <span>Loading templates...</span>
        </div>
      )}
      {/* Error State */}
      {error && (
        <div className="text-center p-8 text-error-11">
          <p>{error}</p>
          <Button variant="primary" className="mt-4" onClick={handleRetry}>
            Retry
          </Button>
        </div>
      )}
      {/* Empty State */}
      {!isLoading && !error && templates.length === 0 && (
        <div className="text-center p-12 text-neutral-10">
          <p>No templates found matching your criteria.</p>
        </div>
      )}
      {/* Template Grid */}
      {!isLoading && !error && templates.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4">
          {templates.map((template) => (
            <div
              key={template.id}
              data-testid={`template-card-${template.id}`}
              className={`flex gap-4 p-4 border-2 rounded-xl cursor-pointer transition-all bg-neutral-1 hover:border-primary-9 hover:shadow-lg ${
                selectedTemplateId === template.id
                  ? "border-primary-9 bg-primary-1"
                  : "border-neutral-5"
              }`}
              onClick={() => handleSelectTemplate(template)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  handleSelectTemplate(template);
                }
              }}
            >
              <div className="text-4xl shrink-0">
                {getIconEmoji(template.icon)}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold mb-1 text-neutral-12">
                  {template.name}
                </h3>
                <p className="text-sm text-neutral-10 mb-2 leading-snug">
                  {template.description}
                </p>
                <div className="flex gap-2 flex-wrap">
                  <span
                    className={`py-0.5 px-2 rounded text-xs font-medium ${getAuthTypeBadgeClasses(template.authType)}`}
                  >
                    {template.authType}
                  </span>
                  <span className="py-0.5 px-2 rounded text-xs font-medium bg-neutral-3 text-neutral-11 capitalize">
                    {template.category}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {/* Custom Connection Option */}
          {showCustomOption && (
            <div
              data-testid="custom-connection-card"
              className="flex gap-4 p-4 border-2 border-dashed border-neutral-5 rounded-xl cursor-pointer transition-all bg-neutral-1 hover:border-primary-9 hover:shadow-lg"
              onClick={onCustom}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  onCustom?.();
                }
              }}
            >
              <div className="text-4xl shrink-0">{getIconEmoji("custom")}</div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold mb-1 text-neutral-12">
                  Custom Connection
                </h3>
                <p className="text-sm text-neutral-10 mb-2 leading-snug">
                  Create a custom connection with your own settings
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ConnectionTemplateSelector;
