/**
 * Background Sync Hook
 *
 * Manages offline request queuing and background sync.
 * Provides state and actions for managing queued requests.
 */

import { useState, useEffect, useCallback, useRef } from "react";

const DB_NAME = "mcp-studio-sync-queue";
const STORE_NAME = "requests";
const DB_VERSION = 1;

export interface QueuedRequest {
  id?: string;
  url: string;
  method: string;
  headers?: Record<string, string>;
  body?: string;
  metadata?: Record<string, unknown>;
  timestamp: number;
}

export interface BackgroundSyncState {
  /** Whether background sync is supported */
  isSupported: boolean;
  /** Whether the hook is initialized */
  isInitialized: boolean;
  /** Whether currently online */
  isOnline: boolean;
  /** Whether currently syncing */
  isSyncing: boolean;
  /** Number of pending requests in queue */
  pendingCount: number;
  /** Last sync error */
  lastError: Error | null;
}

/**
 * Queue storage interface for dependency injection
 */
export interface QueueStorage {
  init(): Promise<void>;
  add(request: QueuedRequest): Promise<string>;
  getAll(): Promise<QueuedRequest[]>;
  remove(id: string): Promise<void>;
  clear(): Promise<void>;
}

export interface BackgroundSyncOptions {
  /** Auto-sync when coming back online */
  autoSync?: boolean;
  /** Custom storage implementation for testing */
  storage?: QueueStorage;
}

export interface BackgroundSyncActions {
  /** Queue a request for later execution */
  queueRequest: (
    request: Omit<QueuedRequest, "id" | "timestamp">,
  ) => Promise<void>;
  /** Sync all pending requests now */
  syncNow: () => Promise<void>;
  /** Clear the request queue */
  clearQueue: () => Promise<void>;
  /** Get current queue */
  getQueue: () => QueuedRequest[];
}

export type UseBackgroundSyncReturn = BackgroundSyncState &
  BackgroundSyncActions;

/**
 * In-memory storage implementation (for testing)
 */
export class InMemoryQueueStorage implements QueueStorage {
  private data: Map<string, QueuedRequest> = new Map();
  private autoIncrement = 0;

  async init(): Promise<void> {
    // No-op for in-memory storage
  }

  async add(request: QueuedRequest): Promise<string> {
    const id = String(++this.autoIncrement);
    this.data.set(id, { ...request, id });
    return id;
  }

  async getAll(): Promise<QueuedRequest[]> {
    return Array.from(this.data.values());
  }

  async remove(id: string): Promise<void> {
    this.data.delete(id);
  }

  async clear(): Promise<void> {
    this.data.clear();
    this.autoIncrement = 0;
  }
}

/**
 * IndexedDB storage implementation (for production)
 */
export class IndexedDBQueueStorage implements QueueStorage {
  private db: IDBDatabase | null = null;

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        reject(new Error("Failed to open IndexedDB"));
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, {
            keyPath: "id",
            autoIncrement: true,
          });
        }
      };
    });
  }

  async add(request: QueuedRequest): Promise<string> {
    if (!this.db) throw new Error("Database not initialized");

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      const addRequest = store.add(request);

      addRequest.onsuccess = () => {
        resolve(String(addRequest.result));
      };

      addRequest.onerror = () => {
        reject(new Error("Failed to add request to queue"));
      };
    });
  }

  async getAll(): Promise<QueuedRequest[]> {
    if (!this.db) return [];

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, "readonly");
      const store = transaction.objectStore(STORE_NAME);
      const getAllRequest = store.getAll();

      getAllRequest.onsuccess = () => {
        resolve(getAllRequest.result || []);
      };

      getAllRequest.onerror = () => {
        reject(new Error("Failed to get requests from queue"));
      };
    });
  }

  async remove(id: string): Promise<void> {
    if (!this.db) return;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      const deleteRequest = store.delete(Number(id));

      deleteRequest.onsuccess = () => {
        resolve();
      };

      deleteRequest.onerror = () => {
        reject(new Error("Failed to remove request from queue"));
      };
    });
  }

  async clear(): Promise<void> {
    if (!this.db) return;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      const clearRequest = store.clear();

      clearRequest.onsuccess = () => {
        resolve();
      };

      clearRequest.onerror = () => {
        reject(new Error("Failed to clear queue"));
      };
    });
  }
}

/**
 * Hook to manage background sync and offline request queuing.
 *
 * @param options Configuration options
 * @returns State and actions for managing background sync
 *
 * @example
 * ```tsx
 * const { isOnline, pendingCount, queueRequest, syncNow } = useBackgroundSync();
 *
 * const sendMessage = async (message: string) => {
 *   await queueRequest({
 *     url: '/api/v1/chat/messages',
 *     method: 'POST',
 *     body: JSON.stringify({ message }),
 *   });
 * };
 * ```
 */
export function useBackgroundSync(
  options: BackgroundSyncOptions = {},
): UseBackgroundSyncReturn {
  const { autoSync = true, storage } = options;

  const [isInitialized, setIsInitialized] = useState(false);
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastError, setLastError] = useState<Error | null>(null);
  const [queue, setQueue] = useState<QueuedRequest[]>([]);

  const storageRef = useRef<QueueStorage | null>(storage || null);
  const syncingRef = useRef(false);

  // Check if background sync is supported
  const isSupported =
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    ("indexedDB" in window || storage !== undefined);

  // Initialize storage
  useEffect(() => {
    const init = async () => {
      try {
        // Use provided storage or default to IndexedDB
        if (storage) {
          storageRef.current = storage;
          await storage.init();
          const existingQueue = await storage.getAll();
          setQueue(existingQueue);
        } else if (isSupported && typeof indexedDB !== "undefined") {
          const indexedDBStorage = new IndexedDBQueueStorage();
          await indexedDBStorage.init();
          storageRef.current = indexedDBStorage;
          const existingQueue = await indexedDBStorage.getAll();
          setQueue(existingQueue);
        }
      } catch (error) {
        console.error("Failed to initialize background sync:", error);
      } finally {
        setIsInitialized(true);
      }
    };

    init();
  }, [isSupported, storage]);

  /**
   * Execute a single request
   */
  const executeRequest = useCallback(
    async (request: QueuedRequest): Promise<boolean> => {
      try {
        const response = await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: request.body,
        });

        return response.ok;
      } catch (error) {
        console.error("Request failed:", error);
        return false;
      }
    },
    [],
  );

  /**
   * Remove from queue (both state and storage)
   */
  const removeFromQueue = useCallback(async (id: string): Promise<void> => {
    if (storageRef.current) {
      await storageRef.current.remove(id);
    }
    setQueue((prev) => prev.filter((item) => item.id !== id));
  }, []);

  /**
   * Sync all pending requests
   */
  const syncPendingRequests = useCallback(async (): Promise<void> => {
    if (syncingRef.current || queue.length === 0 || !navigator.onLine) {
      return;
    }

    syncingRef.current = true;
    setIsSyncing(true);
    setLastError(null);

    try {
      for (const request of queue) {
        try {
          const success = await executeRequest(request);
          if (success && request.id) {
            await removeFromQueue(request.id);
          } else {
            setLastError(new Error(`Failed to sync request to ${request.url}`));
          }
        } catch (error) {
          console.error("Sync error:", error);
          setLastError(
            error instanceof Error ? error : new Error(String(error)),
          );
        }
      }
    } finally {
      syncingRef.current = false;
      setIsSyncing(false);
    }
  }, [queue, executeRequest, removeFromQueue]);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      if (autoSync && queue.length > 0) {
        // Trigger sync when coming back online
        syncPendingRequests();
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [autoSync, queue.length, syncPendingRequests]);

  /**
   * Add to queue (both state and storage)
   */
  const addToQueue = useCallback(
    async (request: QueuedRequest): Promise<void> => {
      let id = request.id;
      if (storageRef.current) {
        id = await storageRef.current.add(request);
      } else {
        id = String(Date.now());
      }
      setQueue((prev) => [...prev, { ...request, id }]);
    },
    [],
  );

  /**
   * Queue a request for later execution (or execute immediately if online)
   */
  const queueRequest = useCallback(
    async (request: Omit<QueuedRequest, "id" | "timestamp">): Promise<void> => {
      const fullRequest: QueuedRequest = {
        ...request,
        timestamp: Date.now(),
      };

      // If online, execute immediately
      if (navigator.onLine) {
        const success = await executeRequest(fullRequest);
        if (!success) {
          // If failed, queue for retry
          await addToQueue(fullRequest);
        }
      } else {
        // Queue for later
        await addToQueue(fullRequest);

        // Try to register background sync
        if (isSupported && "serviceWorker" in navigator) {
          try {
            const registration = await navigator.serviceWorker.ready;
            if (registration.sync) {
              await registration.sync.register("sync-requests");
            }
          } catch (error) {
            console.error("Failed to register background sync:", error);
          }
        }
      }
    },
    [isSupported, executeRequest, addToQueue],
  );

  /**
   * Manually trigger sync
   */
  const syncNow = useCallback(async (): Promise<void> => {
    await syncPendingRequests();
  }, [syncPendingRequests]);

  /**
   * Clear all queued requests
   */
  const clearQueue = useCallback(async (): Promise<void> => {
    if (storageRef.current) {
      await storageRef.current.clear();
    }
    setQueue([]);
  }, []);

  /**
   * Get current queue
   */
  const getQueue = useCallback((): QueuedRequest[] => {
    return queue;
  }, [queue]);

  return {
    isSupported,
    isInitialized,
    isOnline,
    isSyncing,
    pendingCount: queue.length,
    lastError,
    queueRequest,
    syncNow,
    clearQueue,
    getQueue,
  };
}
