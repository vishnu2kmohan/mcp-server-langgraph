/**
 * ResourceBrowser Component
 *
 * Displays available MCP resources with search, preview, and read capabilities.
 */

import React, { useState, useCallback, useMemo } from 'react';
import clsx from 'clsx';
import { useMCPResources } from '../../hooks/useMCPResources';
import { EmptyState } from '../Common';
import type { MCPResource } from '../../api/mcp-types';

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
      />
    </svg>
  );
}

export interface ResourceBrowserProps {
  className?: string;
  onResourceSelect?: (resource: MCPResource) => void;
}

function ResourceIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
      />
    </svg>
  );
}

export function ResourceBrowser({ className, onResourceSelect }: ResourceBrowserProps): React.ReactElement {
  const { resources, readResource } = useMCPResources();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedResource, setSelectedResource] = useState<MCPResource | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter resources by search query
  const filteredResources = useMemo(() => {
    if (!searchQuery.trim()) return resources;

    const query = searchQuery.toLowerCase();
    return resources.filter(
      (resource) =>
        resource.uri.toLowerCase().includes(query) ||
        (resource.name?.toLowerCase().includes(query)) ||
        (resource.description?.toLowerCase().includes(query))
    );
  }, [resources, searchQuery]);

  const handleResourceClick = useCallback(
    async (resource: MCPResource) => {
      setSelectedResource(resource);
      setContent(null);
      setError(null);
      setIsLoading(true);
      onResourceSelect?.(resource);

      try {
        const result = await readResource(resource.uri);
        const textContent = result.contents
          .map((c) => (c.text ? c.text : c.blob ? '[Binary data]' : JSON.stringify(c)))
          .join('\n');
        setContent(textContent);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to read resource');
      } finally {
        setIsLoading(false);
      }
    },
    [readResource, onResourceSelect]
  );

  const handleClose = useCallback(() => {
    setSelectedResource(null);
    setContent(null);
    setError(null);
  }, []);

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header with search */}
      <div className="p-3 border-b border-gray-200 dark:border-dark-border">
        <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary uppercase tracking-wider mb-2">
          Resources ({resources.length})
        </h3>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search resources..."
          className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-dark-surface border-gray-300 dark:border-dark-border text-gray-900 dark:text-dark-text placeholder-gray-400 dark:placeholder-dark-textMuted focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Resource list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {filteredResources.length === 0 ? (
          resources.length === 0 ? (
            <EmptyState
              icon={<ResourceIcon className="w-12 h-12" />}
              title="No resources available"
              description="Connect to an MCP server to browse files, data, and other resources."
              suggestions={[
                "Add an MCP server connection",
                "Check server resource configuration",
                "Verify resource permissions"
              ]}
              variant="compact"
            />
          ) : (
            <EmptyState
              icon={<SearchIcon className="w-10 h-10" />}
              title="No matching resources"
              description={`No resources match "${searchQuery}"`}
              actionLabel="Clear Search"
              onAction={() => setSearchQuery('')}
              variant="compact"
            />
          )
        ) : (
          filteredResources.map((resource) => (
            <ResourceCard
              key={resource.uri}
              resource={resource}
              isSelected={selectedResource?.uri === resource.uri}
              onClick={() => handleResourceClick(resource)}
            />
          ))
        )}
      </div>

      {/* Resource detail panel */}
      {selectedResource && (
        <div className="border-t border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-surface">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-dark-border">
            <h4 className="font-medium text-gray-900 dark:text-dark-text truncate">
              {selectedResource.name || selectedResource.uri}
            </h4>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-dark-text"
              aria-label="Close resource details"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-3 max-h-48 overflow-y-auto">
            {isLoading && (
              <div className="text-sm text-gray-500 dark:text-dark-textMuted animate-pulse">
                Loading resource...
              </div>
            )}

            {error && (
              <div className="p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
                <p className="text-sm text-error-700 dark:text-error-400">{error}</p>
              </div>
            )}

            {content && (
              <pre className="text-sm text-gray-700 dark:text-dark-textSecondary whitespace-pre-wrap overflow-x-auto font-mono bg-white dark:bg-dark-bg p-3 rounded-lg border border-gray-200 dark:border-dark-border">
                {content}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface ResourceCardProps {
  resource: MCPResource;
  isSelected?: boolean;
  onClick?: () => void;
}

function ResourceCard({ resource, isSelected = false, onClick }: ResourceCardProps): React.ReactElement {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left p-3 rounded-lg border transition-colors',
        isSelected
          ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-500'
          : 'bg-white dark:bg-dark-surface border-gray-200 dark:border-dark-border hover:bg-gray-50 dark:hover:bg-dark-hover'
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={clsx(
            'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center',
            isSelected
              ? 'bg-primary-500 text-white'
              : 'bg-gray-100 dark:bg-dark-bg text-gray-600 dark:text-dark-textSecondary'
          )}
        >
          <ResourceIcon className="w-5 h-5" />
        </div>

        <div className="flex-1 min-w-0">
          <h4
            className={clsx(
              'font-medium truncate',
              isSelected
                ? 'text-primary-700 dark:text-primary-400'
                : 'text-gray-900 dark:text-dark-text'
            )}
          >
            {resource.name || resource.uri.split('/').pop()}
          </h4>
          <p className="text-xs text-gray-400 dark:text-dark-textMuted truncate">
            {resource.uri}
          </p>
          {resource.description && (
            <p className="text-sm text-gray-500 dark:text-dark-textMuted line-clamp-1 mt-1">
              {resource.description}
            </p>
          )}
          {resource.mimeType && (
            <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-dark-bg text-gray-600 dark:text-dark-textSecondary">
              {resource.mimeType}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
