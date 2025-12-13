import { Outlet, useLocation } from 'react-router-dom';
import { Toaster } from 'sonner';
import { Sidebar } from './components/Layout/Sidebar';

/**
 * Root application component.
 *
 * Provides:
 * - Global toast notifications
 * - Sidebar navigation for studio routes
 * - Outlet for nested routes
 */
export function App() {
  const location = useLocation();
  const isStudioRoute = location.pathname.startsWith('/studio') || location.pathname.startsWith('/admin');

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {isStudioRoute ? (
        <div className="flex">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
        </div>
      ) : (
        <Outlet />
      )}
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
