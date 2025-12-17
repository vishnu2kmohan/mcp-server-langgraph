/**
 * SettingsProperties Component
 *
 * Property panel for settings, showing current configuration
 * and quick access to settings sections.
 */

import { useAppSelector } from "../../../store/hooks";
import { selectUser } from "../../../store/slices/authSlice";
import { selectPersona } from "../../../store/slices/personaSlice";
import type { TabState } from "../../../store/slices/workspaceSlice";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";

// =============================================================================
// Types
// =============================================================================

export interface SettingsPropertiesProps {
  tab: TabState;
  isSectionExpanded: (id: string) => boolean;
  onToggleSection: (id: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function SettingsProperties({
  tab: _tab,
  isSectionExpanded,
  onToggleSection,
}: SettingsPropertiesProps) {
  const user = useAppSelector(selectUser);
  const persona = useAppSelector(selectPersona);

  // Format user display name from available fields
  const userName =
    user?.firstName && user?.lastName
      ? `${user.firstName} ${user.lastName}`
      : user?.username || "Guest";

  // Format roles as comma-separated list or default
  const userRoles = user?.roles?.length ? user.roles.join(", ") : "user";

  // Persona descriptions for display
  const personaDescriptions: Record<string, string> = {
    admin: "Full system access and configuration",
    developer: "Workflow building and API access",
    user: "Standard chat and usage access",
  };

  return (
    <div data-testid="settings-properties">
      <PropertySection
        id="user-info"
        title="User"
        isExpanded={isSectionExpanded("user-info")}
        onToggle={() => onToggleSection("user-info")}
      >
        <PropertyRow label="Name" value={userName} />
        <PropertyRow label="Email" value={user?.email || "N/A"} />
        <PropertyRow label="Roles" value={userRoles} />
      </PropertySection>

      <PropertySection
        id="persona-info"
        title="Persona"
        isExpanded={isSectionExpanded("persona-info")}
        onToggle={() => onToggleSection("persona-info")}
      >
        <PropertyRow label="Active" value={persona || "user"} />
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          {personaDescriptions[persona] || personaDescriptions.user}
        </p>
      </PropertySection>

      <PropertySection
        id="sections-info"
        title="Settings Sections"
        isExpanded={isSectionExpanded("sections-info")}
        onToggle={() => onToggleSection("sections-info")}
      >
        <div className="space-y-1 text-xs">
          <div className="text-gray-600 dark:text-gray-400">• Profile</div>
          <div className="text-gray-600 dark:text-gray-400">• API Keys</div>
          <div className="text-gray-600 dark:text-gray-400">
            • Notifications
          </div>
          <div className="text-gray-600 dark:text-gray-400">• Appearance</div>
          <div className="text-gray-600 dark:text-gray-400">• Security</div>
        </div>
      </PropertySection>
    </div>
  );
}

export default SettingsProperties;
