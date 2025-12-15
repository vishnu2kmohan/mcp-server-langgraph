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
import { ErrorState, ConfirmDialog } from "../components/UI";
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
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
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
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Vector Collections
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Manage Qdrant vector collections for semantic search
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSearchPanel(true)}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <Search size={16} />
              Search Vectors
            </button>
            <button
              onClick={() => setShowUpsertPanel(true)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Upload size={16} />
              Upsert Points
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus size={16} />
              Create Collection
            </button>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && collections.length > 0 && (
        <div className="px-6 py-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <p className="text-red-700 dark:text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {/* Collections Count */}
          <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
            {collections.length}{" "}
            {collections.length === 1 ? "collection" : "collections"} found
          </div>

          {collections.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
              <Database size={48} className="mb-4 opacity-50" />
              <p>No collections found</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus size={16} />
                Create First Collection
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {collections.map((collection) => (
                <div
                  key={collection.name}
                  className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Database size={24} className="text-blue-500" />
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {collection.name}
                        </h3>
                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
                          <span>{collection.vectors_count ?? 0} points</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteCollection(collection.name)}
                      aria-label={`Delete ${collection.name}`}
                      className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                    >
                      <Trash2 size={20} />
                    </button>
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
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Create Collection
            </h2>
            <form onSubmit={handleCreateCollection} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Collection Name
                </label>
                <input
                  type="text"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  placeholder="Collection name"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="vector-size"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Vector Size
                </label>
                <input
                  id="vector-size"
                  type="number"
                  value={newVectorSize}
                  onChange={(e) => setNewVectorSize(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="distance-metric"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Distance Metric
                </label>
                <select
                  id="distance-metric"
                  value={newDistance}
                  onChange={(e) => setNewDistance(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="cosine">Cosine</option>
                  <option value="euclidean">Euclidean</option>
                  <option value="dot">Dot Product</option>
                </select>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Create
                </button>
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
            className="bg-white dark:bg-gray-800 h-full w-full max-w-lg shadow-xl overflow-y-auto"
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Search Vectors
              </h2>
              <button
                onClick={() => {
                  setShowSearchPanel(false);
                  setSearchResults([]);
                  setHasSearched(false);
                }}
                aria-label="Close search"
                className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <form
              onSubmit={handleSearch}
              className="p-6 space-y-4 border-b border-gray-200 dark:border-gray-700"
            >
              <div>
                <label
                  htmlFor="search-collection"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Select Collection
                </label>
                <select
                  id="search-collection"
                  value={searchCollection}
                  onChange={(e) => setSearchCollection(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                >
                  <option value="">Choose a collection</option>
                  {collections.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="search-query"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Search Query
                </label>
                <input
                  id="search-query"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter search query"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="search-limit"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Limit
                </label>
                <input
                  id="search-limit"
                  type="number"
                  min={1}
                  max={100}
                  value={searchLimit}
                  onChange={(e) => setSearchLimit(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
              <button
                type="submit"
                disabled={isSearching}
                className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                {isSearching ? "Searching..." : "Search"}
              </button>
            </form>

            {/* Search Results */}
            <div className="p-6">
              {hasSearched && searchResults.length === 0 && !isSearching && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No results found
                </div>
              )}
              {searchResults.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {searchResults.length} results
                  </h3>
                  {searchResults.map((result) => (
                    <div
                      key={result.id}
                      className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-mono text-gray-500 dark:text-gray-400">
                          ID: {result.id}
                        </span>
                        <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 text-sm rounded">
                          Score: {result.score.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-sm text-gray-700 dark:text-gray-300">
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
            className="bg-white dark:bg-gray-800 h-full w-full max-w-lg shadow-xl overflow-y-auto"
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Upsert Point
              </h2>
              <button
                onClick={() => {
                  setShowUpsertPanel(false);
                  setUpsertSuccess(false);
                  setUpsertError(null);
                }}
                aria-label="Close upsert"
                className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleUpsert} className="p-6 space-y-4">
              {/* Success Message */}
              {upsertSuccess && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-400 text-sm">
                  Point upserted successfully!
                </div>
              )}

              {/* Error Message */}
              {upsertError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
                  Failed to upsert: {upsertError}
                </div>
              )}

              <div>
                <label
                  htmlFor="upsert-collection"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Select Collection
                </label>
                <select
                  id="upsert-collection"
                  value={upsertCollection}
                  onChange={(e) => setUpsertCollection(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                >
                  <option value="">Choose a collection</option>
                  {collections.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="upsert-text"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Text Content
                </label>
                <textarea
                  id="upsert-text"
                  value={upsertText}
                  onChange={(e) => setUpsertText(e.target.value)}
                  placeholder="Enter text content to embed and store"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
                  required
                />
              </div>

              <div>
                <label
                  htmlFor="upsert-metadata"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Metadata (Optional JSON)
                </label>
                <textarea
                  id="upsert-metadata"
                  value={upsertMetadata}
                  onChange={(e) => setUpsertMetadata(e.target.value)}
                  placeholder='{"source": "document.pdf", "page": 1}'
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none font-mono text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={isUpserting}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {isUpserting ? "Upserting..." : "Upsert"}
              </button>
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
