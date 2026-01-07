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

  // Get auth type badge color
  const getAuthTypeBadgeClass = (authType: string): string => {
    switch (authType) {
      case "oauth2":
        return "badge-oauth2";
      case "api_key":
        return "badge-apikey";
      default:
        return "badge-none";
    }
  };

  return (
    <div className="template-selector">
      <h2 className="template-selector-title">Choose a Template</h2>

      {/* Search */}
      <div className="template-search">
        <input
          type="text"
          placeholder="Search templates..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="template-search-input"
        />
      </div>

      {/* Category Filters */}
      <div className="template-category-filters">
        <button
          className={`category-filter-btn ${selectedCategory === null ? "active" : ""}`}
          onClick={() => handleCategoryChange(null)}
        >
          All
        </button>
        {categories.map((category) => (
          <button
            key={category.id}
            className={`category-filter-btn ${selectedCategory === category.id ? "active" : ""}`}
            onClick={() => handleCategoryChange(category.id)}
          >
            {category.name}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="template-loading" data-testid="loading-templates">
          <div className="loading-spinner" />
          <span>Loading templates...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="template-error">
          <p>{error}</p>
          <button onClick={handleRetry} className="retry-btn">
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && templates.length === 0 && (
        <div className="template-empty">
          <p>No templates found matching your criteria.</p>
        </div>
      )}

      {/* Template Grid */}
      {!isLoading && !error && templates.length > 0 && (
        <div className="template-grid">
          {templates.map((template) => (
            <div
              key={template.id}
              data-testid={`template-card-${template.id}`}
              className={`template-card ${selectedTemplateId === template.id ? "selected" : ""}`}
              onClick={() => handleSelectTemplate(template)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  handleSelectTemplate(template);
                }
              }}
            >
              <div className="template-icon">{getIconEmoji(template.icon)}</div>
              <div className="template-info">
                <h3 className="template-name">{template.name}</h3>
                <p className="template-description">{template.description}</p>
                <div className="template-meta">
                  <span
                    className={`auth-badge ${getAuthTypeBadgeClass(template.authType)}`}
                  >
                    {template.authType}
                  </span>
                  <span className="category-badge">{template.category}</span>
                </div>
              </div>
            </div>
          ))}

          {/* Custom Connection Option */}
          {showCustomOption && (
            <div
              data-testid="custom-connection-card"
              className="template-card template-card-custom"
              onClick={onCustom}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  onCustom?.();
                }
              }}
            >
              <div className="template-icon">{getIconEmoji("custom")}</div>
              <div className="template-info">
                <h3 className="template-name">Custom Connection</h3>
                <p className="template-description">
                  Create a custom connection with your own settings
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        .template-selector {
          padding: 1rem;
        }

        .template-selector-title {
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 1rem;
          color: var(--text-primary, #1f2937);
        }

        .template-search {
          margin-bottom: 1rem;
        }

        .template-search-input {
          width: 100%;
          padding: 0.75rem 1rem;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 0.5rem;
          font-size: 1rem;
          transition: border-color 0.2s;
        }

        .template-search-input:focus {
          outline: none;
          border-color: var(--primary-color, #3b82f6);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .template-category-filters {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }

        .category-filter-btn {
          padding: 0.5rem 1rem;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 2rem;
          background: white;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .category-filter-btn:hover {
          background: var(--hover-bg, #f3f4f6);
        }

        .category-filter-btn.active {
          background: var(--primary-color, #3b82f6);
          border-color: var(--primary-color, #3b82f6);
          color: white;
        }

        .template-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 3rem;
          color: var(--text-secondary, #6b7280);
        }

        .loading-spinner {
          width: 2rem;
          height: 2rem;
          border: 3px solid var(--border-color, #e5e7eb);
          border-top-color: var(--primary-color, #3b82f6);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 1rem;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        .template-error {
          text-align: center;
          padding: 2rem;
          color: var(--error-color, #ef4444);
        }

        .retry-btn {
          margin-top: 1rem;
          padding: 0.5rem 1rem;
          background: var(--primary-color, #3b82f6);
          color: white;
          border: none;
          border-radius: 0.375rem;
          cursor: pointer;
        }

        .template-empty {
          text-align: center;
          padding: 3rem;
          color: var(--text-secondary, #6b7280);
        }

        .template-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1rem;
        }

        .template-card {
          display: flex;
          gap: 1rem;
          padding: 1rem;
          border: 2px solid var(--border-color, #e5e7eb);
          border-radius: 0.75rem;
          cursor: pointer;
          transition: all 0.2s;
          background: white;
        }

        .template-card:hover {
          border-color: var(--primary-color, #3b82f6);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .template-card.selected {
          border-color: var(--primary-color, #3b82f6);
          background: rgba(59, 130, 246, 0.05);
        }

        .template-card-custom {
          border-style: dashed;
        }

        .template-icon {
          font-size: 2rem;
          flex-shrink: 0;
        }

        .template-info {
          flex: 1;
          min-width: 0;
        }

        .template-name {
          font-size: 1rem;
          font-weight: 600;
          margin: 0 0 0.25rem;
          color: var(--text-primary, #1f2937);
        }

        .template-description {
          font-size: 0.875rem;
          color: var(--text-secondary, #6b7280);
          margin: 0 0 0.5rem;
          line-height: 1.4;
        }

        .template-meta {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .auth-badge,
        .category-badge {
          padding: 0.125rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .auth-badge {
          background: var(--badge-bg, #f3f4f6);
          color: var(--badge-color, #6b7280);
        }

        .badge-oauth2 {
          background: #dbeafe;
          color: #1d4ed8;
        }

        .badge-apikey {
          background: #fef3c7;
          color: #b45309;
        }

        .badge-none {
          background: #d1fae5;
          color: #047857;
        }

        .category-badge {
          background: var(--category-bg, #f3f4f6);
          color: var(--category-color, #6b7280);
          text-transform: capitalize;
        }
      `}</style>
    </div>
  );
}

export default ConnectionTemplateSelector;
