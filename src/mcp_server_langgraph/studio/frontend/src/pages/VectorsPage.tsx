/**
 * VectorsPage
 *
 * Vector collections management page for Qdrant integration.
 * Allows creating, viewing, and deleting vector collections.
 * Uses RTK Query for data fetching and mutations.
 */

import { useState } from "react";
import {
  Database,
  RefreshCw,
  Trash2,
  Plus,
  X,
  Search,
  Upload,
} from "lucide-react";
// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { ErrorState } from "../components/UI/ErrorState";
import { ConfirmDialog } from "../components/UI/ConfirmDialog";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { Select } from "../components/UI/Select";
import { Textarea } from "../components/UI/Textarea";
import {
  useListVectorCollectionsQuery,
  useCreateVectorCollectionMutation,
  useDeleteVectorCollectionMutation,
  useSearchVectorsTextMutation,
  useUpsertVectorTextMutation,
} from "../api";
import type { VectorSearchResult } from "../types/api";

export function VectorsPage() {
  // RTK Query hooks
  const {
    data: collections = [],
    isLoading,
    error: fetchError,
    refetch,
  } = useListVectorCollectionsQuery();

  const [createCollection] = useCreateVectorCollectionMutation();
  const [deleteCollection] = useDeleteVectorCollectionMutation();
  const [searchVectors, { isLoading: isSearching }] =
    useSearchVectorsTextMutation();
  const [upsertVector, { isLoading: isUpserting }] =
    useUpsertVectorTextMutation();

  // Local UI state
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [newVectorSize, setNewVectorSize] = useState(1536);
  const [newDistance, setNewDistance] = useState("cosine");

  // Search state
  const [showSearchPanel, setShowSearchPanel] = useState(false);
  const [searchCollection, setSearchCollection] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLimit, setSearchLimit] = useState(10);
  const [searchResults, setSearchResults] = useState<VectorSearchResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  // Upsert state
  const [showUpsertPanel, setShowUpsertPanel] = useState(false);
  const [upsertCollection, setUpsertCollection] = useState("");
  const [upsertText, setUpsertText] = useState("");
  const [upsertMetadata, setUpsertMetadata] = useState("");
  const [upsertSuccess, setUpsertSuccess] = useState(false);
  const [upsertError, setUpsertError] = useState<string | null>(null);

  // Delete confirmation state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [collectionToDelete, setCollectionToDelete] = useState<string | null>(
    null,
  );
  const [isDeleting, setIsDeleting] = useState(false);

  // Combine errors
  const error =
    mutationError || (fetchError ? "Failed to load collections" : null);

  const handleRefresh = () => {
    setMutationError(null);
    refetch();
  };

  const handleCreateCollection = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newCollectionName.trim()) return;

    setMutationError(null);
    try {
      // Capitalize: cosine -> Cosine
      const capitalizedDistance =
        newDistance.charAt(0).toUpperCase() + newDistance.slice(1);
      await createCollection({
        name: newCollectionName,
        vectors: {
          size: newVectorSize,
          distance: capitalizedDistance as "Cosine" | "Euclidean" | "Dot",
        },
      }).unwrap();

      // Reset form and close modal
      setNewCollectionName("");
      setNewVectorSize(1536);
      setNewDistance("cosine");
      setShowCreateModal(false);
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to create collection",
      );
    }
  };

  const handleDeleteCollection = (name: string) => {
    // Open the styled confirmation dialog
    setCollectionToDelete(name);
    setShowDeleteDialog(true);
  };

  const confirmDeleteCollection = async () => {
    if (!collectionToDelete) return;

    setIsDeleting(true);
    setMutationError(null);
    try {
      await deleteCollection(collectionToDelete).unwrap();
      setShowDeleteDialog(false);
      setCollectionToDelete(null);
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to delete collection",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDeleteCollection = () => {
    setShowDeleteDialog(false);
    setCollectionToDelete(null);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!searchCollection || !searchQuery.trim()) return;

    setHasSearched(true);
    setMutationError(null);

    try {
      const results = await searchVectors({
        collection_name: searchCollection,
        query_text: searchQuery,
        limit: searchLimit,
      }).unwrap();

      setSearchResults(results || []);
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to search vectors",
      );
    }
  };

  const handleUpsert = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!upsertCollection || !upsertText.trim()) return;

    setUpsertSuccess(false);
    setUpsertError(null);

    try {
      // Parse metadata if provided
      let metadata: Record<string, unknown> = {};
      if (upsertMetadata.trim()) {
        try {
          metadata = JSON.parse(upsertMetadata);
        } catch {
          setUpsertError("Invalid JSON in metadata field");
          return;
        }
      }

      await upsertVector({
        collection_name: upsertCollection,
        text: upsertText,
        metadata,
      }).unwrap();

      // Success - clear form and show success message
      setUpsertText("");
      setUpsertMetadata("");
      setUpsertSuccess(true);
    } catch (err) {
      setUpsertError(
        err instanceof Error ? err.message : "Failed to upsert point",
      );
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-9" />
      </div>
    );
  }

  if (error && collections.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center">
        <ErrorState
          title="Failed to load collections"
          message={error}
          onRetry={handleRefresh}
          variant="fullscreen"
        />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-neutral-1">
      {/* Header */}
      <header className="px-6 py-4 bg-neutral-2 border-b border-neutral-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-12">
              Vector Collections
            </h1>
            <p className="text-sm text-neutral-11">
              Manage Qdrant vector collections for semantic search
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              className="gap-2"
              onClick={() => setShowSearchPanel(true)}
            >
              <Search size={16} />
              Search Vectors
            </Button>
            <Button
              variant="success"
              className="gap-2"
              onClick={() => setShowUpsertPanel(true)}
            >
              <Upload size={16} />
              Upsert Points
            </Button>
            <Button
              variant="primary"
              className="gap-2"
              onClick={() => setShowCreateModal(true)}
            >
              <Plus size={16} />
              Create Collection
            </Button>
            <Button
              variant="secondary"
              className="gap-2"
              onClick={handleRefresh}
            >
              <RefreshCw size={16} />
              Refresh
            </Button>
          </div>
        </div>
      </header>
      {/* Error Banner */}
      {error && collections.length > 0 && (
        <div className="px-6 py-3 bg-error-1/20 border-b border-error-4">
          <p className="text-error-11 text-sm">{error}</p>
        </div>
      )}
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {/* Collections Count */}
          <div className="mb-4 text-sm text-neutral-11">
            {collections.length}{" "}
            {collections.length === 1 ? "collection" : "collections"} found
          </div>

          {collections.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-neutral-11">
              <Database size={48} className="mb-4 opacity-50" />
              <p>No collections found</p>
              <Button
                variant="primary"
                className="mt-4 gap-2"
                onClick={() => setShowCreateModal(true)}
              >
                <Plus size={16} />
                Create First Collection
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {collections.map((collection) => (
                <div
                  key={collection.name}
                  className="bg-neutral-2 rounded-lg border border-neutral-6 p-6"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Database size={24} className="text-primary-9" />
                      <div>
                        <h3 className="text-lg font-semibold text-neutral-12">
                          {collection.name}
                        </h3>
                        <div className="flex items-center gap-4 mt-1 text-sm text-neutral-11">
                          <span>{collection.vectors_count ?? 0} points</span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="danger"
                      className="p-2 text-error-9 hover:bg-error-1 dark:hover:bg-error-12/20 rounded"
                      onClick={() => handleDeleteCollection(collection.name)}
                      aria-label={`Delete ${collection.name}`}
                    >
                      <Trash2 size={20} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-neutral-2 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-neutral-12 mb-4">
              Create Collection
            </h2>
            <form onSubmit={handleCreateCollection} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-11 mb-2">
                  Collection Name
                </label>
                <Input
                  className="px-3 py-2 text-neutral-12"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  placeholder="Collection name"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="vector-size"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Vector Size
                </label>
                <Input
                  className="px-3 py-2 text-neutral-12"
                  id="vector-size"
                  type="number"
                  value={newVectorSize}
                  onChange={(e) => setNewVectorSize(parseInt(e.target.value))}
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="distance-metric"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Distance Metric
                </label>
                <Select
                  className="px-3 py-2 text-neutral-12"
                  id="distance-metric"
                  value={newDistance}
                  onChange={(e) => setNewDistance(e.target.value)}
                >
                  <option value="cosine">Cosine</option>
                  <option value="euclidean">Euclidean</option>
                  <option value="dot">Dot Product</option>
                </Select>
              </div>
              <div className="flex gap-2 justify-end">
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </Button>
                <Button variant="primary" type="submit">
                  Create
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Search Panel */}
      {showSearchPanel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-end z-50">
          <div
            data-testid="vector-search-panel"
            className="bg-neutral-2 h-full w-full max-w-lg shadow-xl overflow-y-auto"
          >
            <div className="px-6 py-4 border-b border-neutral-6 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-neutral-12">
                Search Vectors
              </h2>
              <Button
                variant="secondary"
                className="p-2 text-neutral-11 hover:bg-neutral-21 dark:hover:bg-neutral-10 rounded"
                onClick={() => {
                  setShowSearchPanel(false);
                  setSearchResults([]);
                  setHasSearched(false);
                }}
                aria-label="Close search"
              >
                <X size={20} />
              </Button>
            </div>

            <form
              onSubmit={handleSearch}
              className="p-6 space-y-4 border-b border-neutral-6"
            >
              <div>
                <label
                  htmlFor="search-collection"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Select Collection
                </label>
                <Select
                  className="px-3 py-2 text-neutral-12"
                  id="search-collection"
                  value={searchCollection}
                  onChange={(e) => setSearchCollection(e.target.value)}
                  required
                >
                  <option value="">Choose a collection</option>
                  {collections.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label
                  htmlFor="search-query"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Search Query
                </label>
                <Input
                  className="px-3 py-2 text-neutral-12"
                  id="search-query"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter search query"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="search-limit"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Limit
                </label>
                <Input
                  className="px-3 py-2 text-neutral-12"
                  id="search-limit"
                  type="number"
                  min={1}
                  max={100}
                  value={searchLimit}
                  onChange={(e) => setSearchLimit(parseInt(e.target.value))}
                />
              </div>
              <Button
                variant="primary"
                fullWidth
                type="submit"
                disabled={isSearching}
              >
                {isSearching ? "Searching..." : "Search"}
              </Button>
            </form>

            {/* Search Results */}
            <div className="p-6">
              {hasSearched && searchResults.length === 0 && !isSearching && (
                <div className="text-center py-8 text-neutral-11">
                  No results found
                </div>
              )}
              {searchResults.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-neutral-11">
                    {searchResults.length} results
                  </h3>
                  {searchResults.map((result) => (
                    <div
                      key={result.id}
                      className="p-4 bg-neutral-1 rounded-lg border border-neutral-6"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-mono text-neutral-11">
                          ID: {result.id}
                        </span>
                        <span className="px-2 py-0.5 bg-insight-2 text-insight-11 text-sm rounded">
                          Score: {result.score.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-sm text-neutral-11">
                        {result.payload?.text
                          ? String(result.payload.text)
                          : JSON.stringify(result.payload ?? {})}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {/* Upsert Panel */}
      {showUpsertPanel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-end z-50">
          <div
            data-testid="vector-upsert-panel"
            className="bg-neutral-2 h-full w-full max-w-lg shadow-xl overflow-y-auto"
          >
            <div className="px-6 py-4 border-b border-neutral-6 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-neutral-12">
                Upsert Point
              </h2>
              <Button
                variant="secondary"
                className="p-2 text-neutral-11 hover:bg-neutral-21 dark:hover:bg-neutral-10 rounded"
                onClick={() => {
                  setShowUpsertPanel(false);
                  setUpsertSuccess(false);
                  setUpsertError(null);
                }}
                aria-label="Close upsert"
              >
                <X size={20} />
              </Button>
            </div>

            <form onSubmit={handleUpsert} className="p-6 space-y-4">
              {/* Success Message */}
              {upsertSuccess && (
                <div className="p-3 bg-success-1/20 border border-success-4 rounded-lg text-success-11 text-sm">
                  Point upserted successfully!
                </div>
              )}

              {/* Error Message */}
              {upsertError && (
                <div className="p-3 bg-error-1/20 border border-error-4 rounded-lg text-error-11 text-sm">
                  Failed to upsert: {upsertError}
                </div>
              )}

              <div>
                <label
                  htmlFor="upsert-collection"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Select Collection
                </label>
                <Select
                  className="px-3 py-2 text-neutral-12"
                  id="upsert-collection"
                  value={upsertCollection}
                  onChange={(e) => setUpsertCollection(e.target.value)}
                  required
                >
                  <option value="">Choose a collection</option>
                  {collections.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <label
                  htmlFor="upsert-text"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Text Content
                </label>
                <Textarea
                  className="px-3 py-2 text-neutral-12 resize-none"
                  id="upsert-text"
                  value={upsertText}
                  onChange={(e) => setUpsertText(e.target.value)}
                  placeholder="Enter text content to embed and store"
                  rows={4}
                  required
                />
              </div>

              <div>
                <label
                  htmlFor="upsert-metadata"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Metadata (Optional JSON)
                </label>
                <Textarea
                  className="px-3 py-2 text-neutral-12 resize-none font-mono text-sm"
                  id="upsert-metadata"
                  value={upsertMetadata}
                  onChange={(e) => setUpsertMetadata(e.target.value)}
                  placeholder='{"source": "document.pdf", "page": 1}'
                  rows={3}
                />
              </div>

              <Button
                variant="success"
                fullWidth
                type="submit"
                disabled={isUpserting}
              >
                {isUpserting ? "Upserting..." : "Upsert"}
              </Button>
            </form>
          </div>
        </div>
      )}
      {/* Delete Collection Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onClose={cancelDeleteCollection}
        onConfirm={confirmDeleteCollection}
        title="Delete Collection"
        message={`Are you sure you want to delete the collection "${collectionToDelete}"? This action cannot be undone and all vectors will be permanently removed.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={isDeleting}
      />
    </div>
  );
}

export default VectorsPage;
