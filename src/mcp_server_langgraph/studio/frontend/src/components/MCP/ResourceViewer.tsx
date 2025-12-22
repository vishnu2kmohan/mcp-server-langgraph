/**
 * ResourceViewer Component
 *
 * A dialog for viewing MCP resources with support for text and binary content.
 *
 * Features:
 * - List available resources with metadata
 * - Read resource content on selection
 * - Display text content with syntax highlighting
 * - Display binary content (images) inline
 * - Copy content to clipboard
 */

import React, { useState, useCallback, useEffect, useMemo } from "react";
import {
  useListMcpResourcesQuery,
  useReadMcpResourceMutation,
} from "../../api";

interface ResourceViewerProps {
  open: boolean;
  onClose: () => void;
}

interface ResourceContent {
  uri: string;
  mime_type: string | null;
  text: string | null;
  blob: string | null;
}

export function ResourceViewer({ open, onClose }: ResourceViewerProps) {
  const {
    data: resourcesData,
    isLoading: isLoadingResources,
    error: resourcesError,
  } = useListMcpResourcesQuery();
  const [readResource, { isLoading: isReadingContent }] =
    useReadMcpResourceMutation();

  const [selectedUri, setSelectedUri] = useState<string | null>(null);
  const [content, setContent] = useState<ResourceContent | null>(null);
  const [readError, setReadError] = useState<string | null>(null);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedUri(null);
      setContent(null);
      setReadError(null);
    }
  }, [open]);

  // Get selected resource details
  const selectedResource = useMemo(() => {
    if (!selectedUri || !resourcesData?.resources) return null;
    return (
      resourcesData.resources.find((r) => r.uri === selectedUri) || null
    );
  }, [selectedUri, resourcesData?.resources]);

  // Handle resource selection
  const handleResourceSelect = useCallback(
    async (uri: string) => {
      setSelectedUri(uri);
      setContent(null);
      setReadError(null);

      try {
        const response = await readResource({ uri }).unwrap();
        if (response.contents && response.contents.length > 0) {
          setContent(response.contents[0]);
        }
      } catch (error) {
        setReadError("Failed to read resource");
      }
    },
    [readResource]
  );

  // Handle copy to clipboard
  const handleCopy = useCallback(async () => {
    if (content?.text) {
      await navigator.clipboard.writeText(content.text);
    }
  }, [content]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="resource-viewer-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog content */}
      <div className="relative z-10 flex h-[80vh] w-full max-w-4xl flex-col rounded-lg bg-white shadow-xl dark:bg-gray-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
          <h2
            id="resource-viewer-title"
            className="text-xl font-semibold text-gray-900 dark:text-white"
          >
            Resource Viewer
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
            aria-label="Close"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Loading state */}
        {isLoadingResources && (
          <div className="flex flex-1 items-center justify-center">
            <span className="text-gray-500">Loading resources...</span>
          </div>
        )}

        {/* Error state */}
        {resourcesError && (
          <div className="flex flex-1 items-center justify-center">
            <div className="rounded-md bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
              Error loading resources. Please try again.
            </div>
          </div>
        )}

        {/* Main content */}
        {!isLoadingResources && !resourcesError && (
          <div className="flex flex-1 overflow-hidden">
            {/* Resource list */}
            <div className="w-1/3 overflow-y-auto border-r border-gray-200 dark:border-gray-700">
              {resourcesData?.resources.length === 0 ? (
                <div className="p-4 text-center text-gray-500">
                  No resources available
                </div>
              ) : (
                <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                  {resourcesData?.resources.map((resource) => (
                    <li key={resource.uri}>
                      <button
                        type="button"
                        onClick={() => handleResourceSelect(resource.uri)}
                        className={`w-full p-3 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-700 ${
                          selectedUri === resource.uri
                            ? "bg-blue-50 dark:bg-blue-900/20"
                            : ""
                        }`}
                      >
                        <div className="font-medium text-gray-900 dark:text-white">
                          {resource.name}
                        </div>
                        {resource.title && (
                          <div className="text-sm text-gray-600 dark:text-gray-400">
                            {resource.title}
                          </div>
                        )}
                        <div className="mt-1 text-xs text-gray-500 dark:text-gray-500">
                          {resource.mime_type}
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Content panel */}
            <div className="flex w-2/3 flex-col overflow-hidden">
              {/* Resource details */}
              {selectedResource && (
                <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    {selectedResource.name}
                  </h3>
                  {selectedResource.description && (
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      {selectedResource.description}
                    </p>
                  )}
                </div>
              )}

              {/* Content display */}
              <div className="flex-1 overflow-auto p-4">
                {!selectedUri && (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    Select a resource to view its content
                  </div>
                )}

                {isReadingContent && (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    Loading content...
                  </div>
                )}

                {readError && (
                  <div className="rounded-md bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                    {readError}
                  </div>
                )}

                {content && !isReadingContent && (
                  <div className="relative">
                    {/* Copy button */}
                    {content.text && (
                      <button
                        type="button"
                        onClick={handleCopy}
                        className="absolute right-2 top-2 rounded-md bg-gray-100 p-2 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                        aria-label="Copy"
                      >
                        <svg
                          className="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                          />
                        </svg>
                      </button>
                    )}

                    {/* Text content */}
                    {content.text && (
                      <pre className="whitespace-pre-wrap rounded-md bg-gray-50 p-4 text-sm text-gray-800 dark:bg-gray-900 dark:text-gray-200">
                        {content.text}
                      </pre>
                    )}

                    {/* Binary content (image) */}
                    {content.blob && content.mime_type?.startsWith("image/") && (
                      <img
                        src={`data:${content.mime_type};base64,${content.blob}`}
                        alt={selectedResource?.name || "Resource content"}
                        className="max-w-full rounded-md"
                      />
                    )}

                    {/* Binary content (other) */}
                    {content.blob &&
                      !content.mime_type?.startsWith("image/") && (
                        <div className="rounded-md bg-gray-50 p-4 dark:bg-gray-900">
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Binary content ({content.mime_type})
                          </p>
                          <p className="mt-2 text-xs text-gray-500">
                            {content.blob.length} characters (base64 encoded)
                          </p>
                        </div>
                      )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ResourceViewer;
