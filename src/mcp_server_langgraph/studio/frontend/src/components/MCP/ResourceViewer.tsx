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

import { useState, useCallback, useEffect, useMemo } from "react";
import {
  useListMcpResourcesQuery,
  useReadMcpResourceMutation,
} from "../../api";

import { Button } from "@/components/UI";

export interface ResourceViewerProps {
  open: boolean;
  onClose: () => void;
  /** Optional resource URI to pre-select when dialog opens */
  preselectedResourceUri?: string;
}

interface ResourceContent {
  uri: string;
  mimeType: string | null;
  text: string | null;
  blob: string | null;
}

export function ResourceViewer({
  open,
  onClose,
  preselectedResourceUri,
}: ResourceViewerProps) {
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
  const [hasPreselected, setHasPreselected] = useState(false);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedUri(null);
      setContent(null);
      setReadError(null);
      setHasPreselected(false);
    }
  }, [open]);

  // Get selected resource details
  const selectedResource = useMemo(() => {
    if (!selectedUri || !resourcesData?.resources) return null;
    return resourcesData.resources.find((r) => r.uri === selectedUri) || null;
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
          const item = response.contents[0];
          if (item) {
            setContent({
              uri: item.uri,
              mimeType: item.mimeType ?? null,
              text: item.text ?? null,
              blob: item.blob ?? null,
            });
          }
        }
      } catch {
        setReadError("Failed to read resource");
      }
    },
    [readResource],
  );

  // Pre-select resource when preselectedResourceUri is provided
  useEffect(() => {
    if (
      open &&
      preselectedResourceUri &&
      resourcesData?.resources &&
      !hasPreselected
    ) {
      // Validate the resource exists
      const resourceExists = resourcesData.resources.some(
        (r) => r.uri === preselectedResourceUri,
      );
      if (resourceExists) {
        setHasPreselected(true);
        handleResourceSelect(preselectedResourceUri);
      }
    }
  }, [
    open,
    preselectedResourceUri,
    resourcesData?.resources,
    hasPreselected,
    handleResourceSelect,
  ]);

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
        className="absolute inset-0 bg-neutral-a6"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Dialog content */}
      <div className="relative z-10 flex h-[80vh] w-full max-w-4xl flex-col rounded-lg bg-neutral-1 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-5 p-4">
          <h2
            id="resource-viewer-title"
            className="text-xl font-semibold text-neutral-12"
          >
            Resource Viewer
          </h2>
          <Button
            variant="secondary"
            className="rounded-md p-2 text-neutral-10 hover:bg-neutral-2 hover:text-neutral-11"
            type="button"
            onClick={onClose}
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
          </Button>
        </div>

        {/* Loading state */}
        {isLoadingResources && (
          <div className="flex flex-1 items-center justify-center">
            <span className="text-neutral-10">
              Loading resources...
            </span>
          </div>
        )}

        {/* Error state */}
        {resourcesError && (
          <div className="flex flex-1 items-center justify-center">
            <div className="rounded-md bg-error-1 p-4 text-error-11 dark:bg-error-a3 dark:text-error-7">
              Error loading resources. Please try again.
            </div>
          </div>
        )}

        {/* Main content */}
        {!isLoadingResources && !resourcesError && (
          <div className="flex flex-1 overflow-hidden">
            {/* Resource list */}
            <div className="w-1/3 overflow-y-auto border-r border-neutral-5">
              {resourcesData?.resources.length === 0 ? (
                <div className="p-4 text-center text-neutral-10">
                  No resources available
                </div>
              ) : (
                <ul className="divide-y divide-neutral-5 dark:divide-neutral-6">
                  {resourcesData?.resources.map((resource) => (
                    <li key={resource.uri}>
                      <Button
                        variant="secondary"
                        className="w-full p-3 text-left hover:bg-neutral-1"
                        type="button"
                        onClick={() => handleResourceSelect(resource.uri)}
                      >
                        <div className="font-medium text-neutral-12">
                          {resource.name}
                        </div>
                        {resource.title && (
                          <div className="text-sm text-neutral-11">
                            {resource.title}
                          </div>
                        )}
                        <div className="mt-1 text-xs text-neutral-10">
                          {resource.mimeType}
                        </div>
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Content panel */}
            <div className="flex w-2/3 flex-col overflow-hidden">
              {/* Resource details */}
              {selectedResource && (
                <div className="border-b border-neutral-5 p-4">
                  <h3 className="font-medium text-neutral-12">
                    {selectedResource.name}
                  </h3>
                  {selectedResource.description && (
                    <p className="mt-1 text-sm text-neutral-11">
                      {selectedResource.description}
                    </p>
                  )}
                </div>
              )}

              {/* Content display */}
              <div className="flex-1 overflow-auto p-4">
                {!selectedUri && (
                  <div className="flex h-full items-center justify-center text-neutral-10">
                    Select a resource to view its content
                  </div>
                )}

                {isReadingContent && (
                  <div className="flex h-full items-center justify-center text-neutral-10">
                    Loading content...
                  </div>
                )}

                {readError && (
                  <div className="rounded-md bg-error-1 p-4 text-error-11 dark:bg-error-a3 dark:text-error-7">
                    {readError}
                  </div>
                )}

                {content && !isReadingContent && (
                  <div className="relative">
                    {/* Copy button */}
                    {content.text && (
                      <Button
                        variant="secondary"
                        className="absolute right-2 top-2 rounded-md bg-neutral-2 p-2 text-neutral-11 hover:bg-neutral-3"
                        type="button"
                        onClick={handleCopy}
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
                      </Button>
                    )}

                    {/* Text content */}
                    {content.text && (
                      <pre className="whitespace-pre-wrap rounded-md bg-neutral-1 p-4 text-sm text-neutral-12">
                        {content.text}
                      </pre>
                    )}

                    {/* Binary content (image) */}
                    {content.blob && content.mimeType?.startsWith("image/") && (
                      <img
                        src={`data:${content.mimeType};base64,${content.blob}`}
                        alt={selectedResource?.name || "Resource content"}
                        className="max-w-full rounded-md"
                      />
                    )}

                    {/* Binary content (other) */}
                    {content.blob &&
                      !content.mimeType?.startsWith("image/") && (
                        <div className="rounded-md bg-neutral-1 p-4">
                          <p className="text-sm text-neutral-11">
                            Binary content ({content.mimeType})
                          </p>
                          <p className="mt-2 text-xs text-neutral-10">
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
