/**
 * Sidebar Component
 *
 * Persistent navigation sidebar for the Studio application.
 * Provides navigation links to all major sections with active state highlighting.
 */

import { NavLink } from 'react-router-dom';

/**
 * Navigation item configuration
 */
interface NavItem {
  path: string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/studio/chat', label: 'Chat' },
  { path: '/studio/sessions', label: 'Sessions' },
  { path: '/studio/workflows', label: 'Workflows' },
  { path: '/studio/mcp', label: 'MCP' },
  { path: '/studio/observability', label: 'Observability' },
  { path: '/studio/cost', label: 'Cost' },
  { path: '/studio/settings', label: 'Settings' },
  { path: '/admin/dashboard', label: 'Admin' },
];

/**
 * Get CSS classes for nav links based on active state
 */
function getNavLinkClasses({ isActive }: { isActive: boolean }): string {
  const baseClasses =
    'flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors';
  const activeClasses = 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
  const inactiveClasses =
    'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800';

  return `${baseClasses} ${isActive ? activeClasses : inactiveClasses}`;
}

/**
 * Sidebar navigation component
 */
export function Sidebar() {
  return (
    <nav
      className="w-64 h-screen bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col"
      role="navigation"
    >
      <div className="p-6">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">
          LangGraph Studio
        </h1>
      </div>

      <div className="flex-1 px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.path} to={item.path} className={getNavLinkClasses}>
            {item.label}
          </NavLink>
        ))}
      </div>

      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          v0.1.0
        </p>
      </div>
    </nav>
  );
}
