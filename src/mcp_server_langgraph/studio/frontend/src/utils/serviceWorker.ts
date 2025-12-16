/**
 * Service Worker Registration Utility
 *
 * Handles registration and unregistration of service workers
 * for PWA offline support.
 */

/**
 * Register the service worker for offline caching.
 * @returns Promise that resolves to true if registration succeeds, false otherwise
 */
export async function registerServiceWorker(): Promise<boolean> {
  // Check if service worker is supported
  if (!("serviceWorker" in navigator)) {
    console.log("Service workers are not supported in this browser");
    return false;
  }

  try {
    // Use import.meta.env.BASE_URL to respect Vite's base path configuration
    // In production: BASE_URL = '/studio/' -> sw.js at /studio/sw.js
    // In development: BASE_URL = '/' -> sw.js at /sw.js
    const basePath = import.meta.env.BASE_URL || "/";
    const swPath = `${basePath}sw.js`;

    const registration = await navigator.serviceWorker.register(swPath, {
      scope: basePath,
    });
    console.log("Service worker registered:", registration);
    return true;
  } catch (error) {
    console.error("Service worker registration failed:", error);
    return false;
  }
}

/**
 * Unregister all service workers.
 * Useful for clearing cache or disabling offline functionality.
 * @returns Promise that resolves to true if unregistration succeeds, false otherwise
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  // Check if service worker is supported
  if (!("serviceWorker" in navigator)) {
    return false;
  }

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((reg) => reg.unregister()));
    console.log("All service workers unregistered");
    return true;
  } catch (error) {
    console.error("Service worker unregistration failed:", error);
    return false;
  }
}
