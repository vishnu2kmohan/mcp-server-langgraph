import { Outlet } from 'react-router-dom';
import { Toaster } from 'sonner';

/**
 * Root application component.
 *
 * Provides:
 * - Global toast notifications
 * - Outlet for nested routes
 */
export function App() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <Outlet />
      <Toaster
        position="bottom-right"
        richColors
        toastOptions={{
          duration: 4000,
          classNames: {
            toast: 'font-sans',
          },
        }}
      />
    </div>
  );
}
