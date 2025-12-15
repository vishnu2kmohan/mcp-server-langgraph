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
    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
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
