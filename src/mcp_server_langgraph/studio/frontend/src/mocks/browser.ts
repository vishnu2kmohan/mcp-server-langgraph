/**
 * MSW Browser Worker
 *
 * Sets up MSW for browser environments (development and Storybook).
 * This enables API mocking in the browser for development without a backend.
 *
 * To enable in development, add to main.tsx:
 *
 *   if (import.meta.env.DEV && import.meta.env.VITE_MSW_ENABLED === 'true') {
 *     const { worker } = await import('./mocks/browser');
 *     await worker.start({ onUnhandledRequest: 'bypass' });
 *   }
 *
 * Then run with: VITE_MSW_ENABLED=true npm run dev
 */

import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

// Create the browser worker with default handlers
export const worker = setupWorker(...handlers);

// Re-export handlers for runtime customization
export { handlers };
