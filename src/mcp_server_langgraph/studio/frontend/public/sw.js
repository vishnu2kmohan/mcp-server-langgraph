/**
 * Service Worker for Agent Studio PWA
 *
 * Provides offline caching for static assets and API responses.
 * Uses cache-first strategy for assets and network-first for API calls.
 */

const CACHE_NAME = "agent-studio-v1";
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/manifest.json",
];

// Install event - cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Service worker: caching static assets");
      return cache.addAll(STATIC_ASSETS);
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log("Service worker: deleting old cache", name);
            return caches.delete(name);
          })
      );
    })
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch event - serve from cache or network
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") {
    return;
  }

  // Skip API calls and WebSocket connections - always go to network
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/")) {
    event.respondWith(
      fetch(request).catch(() => {
        // Return offline response for API calls
        return new Response(
          JSON.stringify({ error: "offline", message: "You are currently offline" }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          }
        );
      })
    );
    return;
  }

  // Cache-first strategy for static assets
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Return cached response and update cache in background
        fetch(request)
          .then((networkResponse) => {
            if (networkResponse.ok) {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, networkResponse.clone());
              });
            }
          })
          .catch(() => {
            // Network failed, but we have cache - that's fine
          });
        return cachedResponse;
      }

      // Not in cache - try network
      return fetch(request)
        .then((networkResponse) => {
          // Cache successful responses
          if (networkResponse.ok) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Return offline page for navigation requests
          if (request.mode === "navigate") {
            return caches.match("/index.html");
          }
          // For other requests, just fail
          throw new Error("Network unavailable");
        });
    })
  );
});

// Handle messages from the app
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

// =============================================================================
// Push Notification Handlers
// =============================================================================

/**
 * Handle incoming push notifications.
 * Displays a notification based on the push data payload.
 */
self.addEventListener("push", (event) => {
  let data = {};

  // Parse push data (can be JSON or text)
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    // If not JSON, use text as body
    data = {
      title: "MCP Server Alert",
      body: event.data ? event.data.text() : "New notification",
    };
  }

  const options = {
    body: data.body || "New notification",
    icon: data.icon || "/icons/icon-192.png",
    badge: data.badge || "/icons/badge-72.png",
    tag: data.tag || "default",
    data: data.data || {},
    actions: data.actions || [],
    // Vibration pattern: [vibrate, pause, vibrate, pause, vibrate]
    vibrate: [200, 100, 200],
    // Require user interaction for critical alerts
    requireInteraction: data.data?.type === "critical_alert",
    // Renotify even if same tag (for updates)
    renotify: true,
  };

  const title = data.title || "MCP Server";

  event.waitUntil(self.registration.showNotification(title, options));
});

/**
 * Handle notification click events.
 * Opens the app to the appropriate page based on notification data.
 */
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const data = event.notification.data || {};
  let targetUrl = "/";

  // Determine target URL based on notification type
  if (data.type === "critical_alert" && data.alert_id) {
    targetUrl = `/admin?tab=alerts&alert=${data.alert_id}`;
  }

  // Handle notification action buttons
  if (event.action === "view") {
    // View action - navigate to the alert
    if (data.alert_id) {
      targetUrl = `/admin?tab=alerts&alert=${data.alert_id}`;
    }
  } else if (event.action === "dismiss") {
    // Dismiss action - just close (already done above)
    return;
  }

  // Open or focus the app window
  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((windowClients) => {
        // Check if there's already a window open
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin)) {
            // Navigate existing window and focus it
            client.navigate(targetUrl);
            return client.focus();
          }
        }
        // No existing window - open a new one
        return clients.openWindow(targetUrl);
      })
  );
});

/**
 * Handle notification close events (user dismissed without clicking).
 * Can be used for analytics tracking.
 */
self.addEventListener("notificationclose", (event) => {
  const data = event.notification.data || {};
  console.log("Notification closed:", data.type, data.alert_id);
  // Future: Send analytics event for dismissed notifications
});

/**
 * Handle push subscription change events.
 * Re-subscribes the user if their subscription expires.
 */
self.addEventListener("pushsubscriptionchange", (event) => {
  console.log("Push subscription changed");

  event.waitUntil(
    // Get the new subscription
    self.registration.pushManager
      .subscribe({
        userVisibleOnly: true,
        // Application server key should be passed here in production
        // This would typically be fetched from an API endpoint
      })
      .then((newSubscription) => {
        // Send the new subscription to the server
        return fetch("/api/v1/notifications/push/resubscribe", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            old_endpoint: event.oldSubscription?.endpoint,
            new_subscription: newSubscription.toJSON(),
          }),
        });
      })
      .catch((error) => {
        console.error("Failed to resubscribe to push:", error);
      })
  );
});
