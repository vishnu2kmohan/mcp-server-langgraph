/**
 * SkillsPage
 *
 * Skills marketplace page for browsing, installing, and managing skills.
 * Provides tabbed interface for:
 * - Browse: Discover skills from marketplaces
 * - Installed: Manage locally installed skills
 * - Updates: Check for and apply skill updates
 */

import { useState, useMemo } from "react";
import {
  Package,
  Download,
  Trash2,
  RefreshCw,
  Search,
  Filter,
  CheckCircle,
  AlertCircle,
  Loader2,
  Store,
  HardDrive,
  ArrowUpCircle,
  Lock,
} from "lucide-react";
import {
  useListMarketplaceSkillsQuery,
  useInstallSkillMutation,
  useListInstalledSkillsQuery,
  useUninstallSkillMutation,
  useCheckSkillUpdatesQuery,
  useApplySkillUpdatesMutation,
  type SkillMetadata,
} from "../api";
import { useFeatureFlags } from "../contexts/FeatureFlagContext";

type SkillsTab = "browse" | "installed" | "updates";

/** Helper to extract error message from RTK Query errors */
function getErrorMessage(error: unknown): string {
  if (!error) return "An unknown error occurred";

  // RTK Query FetchBaseQueryError with data
  if (typeof error === "object" && error !== null) {
    const errObj = error as Record<string, unknown>;

    // Check for 403 status
    if (errObj.status === 403) {
      return "You don't have permission to perform this action. Contact your administrator if you believe this is an error.";
    }

    // Check for detail message (FastAPI format)
    if (errObj.data && typeof errObj.data === "object") {
      const data = errObj.data as Record<string, unknown>;
      if (typeof data.detail === "string") {
        return data.detail;
      }
    }

    // Check for message property
    if (typeof errObj.message === "string") {
      return errObj.message;
    }
  }

  return "An unexpected error occurred. Please try again.";
}

export function SkillsPage() {
  const [activeTab, setActiveTab] = useState<SkillsTab>("browse");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);

  // Feature flag check
  const { isEnabled, isLoading: isFlagsLoading } = useFeatureFlags();
  const isMarketplaceEnabled = isEnabled("enable_skills_marketplace");

  // RTK Query hooks - must be called before any early returns (React rules of hooks)
  const {
    data: marketplaceData,
    isLoading: isLoadingMarketplace,
    error: marketplaceError,
    refetch: refetchMarketplace,
  } = useListMarketplaceSkillsQuery(
    {
      search: searchQuery || undefined,
      tags: selectedTags.length > 0 ? selectedTags : undefined,
    },
    { skip: !isMarketplaceEnabled },
  );

  const {
    data: installedData,
    isLoading: isLoadingInstalled,
    refetch: refetchInstalled,
  } = useListInstalledSkillsQuery(undefined, { skip: !isMarketplaceEnabled });

  const {
    data: updatesData,
    isLoading: isLoadingUpdates,
    refetch: refetchUpdates,
  } = useCheckSkillUpdatesQuery(undefined, { skip: !isMarketplaceEnabled });

  const [installSkill, { isLoading: isInstalling }] = useInstallSkillMutation();
  const [uninstallSkill, { isLoading: isUninstalling }] =
    useUninstallSkillMutation();
  const [applyUpdates, { isLoading: isApplyingUpdates }] =
    useApplySkillUpdatesMutation();

  // Filtered skills based on search
  const filteredSkills = useMemo(() => {
    if (!marketplaceData?.skills) return [];
    if (!searchQuery) return marketplaceData.skills;

    const query = searchQuery.toLowerCase();
    return marketplaceData.skills.filter(
      (skill) =>
        skill.name.toLowerCase().includes(query) ||
        skill.description.toLowerCase().includes(query),
    );
  }, [marketplaceData?.skills, searchQuery]);

  // Extract unique tags for filtering
  const availableTags = useMemo(() => {
    if (!marketplaceData?.skills) return [];
    const tagSet = new Set<string>();
    marketplaceData.skills.forEach((skill) => {
      skill.tags?.forEach((tag) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [marketplaceData?.skills]);

  // Show disabled state if feature is not enabled (after all hooks)
  if (!isFlagsLoading && !isMarketplaceEnabled) {
    return (
      <div className="flex flex-col h-full bg-surface-primary">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <Package className="w-6 h-6 text-text-tertiary" />
            <h1 className="text-xl font-semibold text-text-primary">
              Skills Marketplace
            </h1>
          </div>
        </div>

        {/* Disabled State */}
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center text-center max-w-md px-6">
            <div className="w-16 h-16 rounded-full bg-surface-secondary flex items-center justify-center mb-4">
              <Lock className="w-8 h-8 text-text-tertiary" />
            </div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">
              Skills Marketplace Disabled
            </h2>
            <p className="text-text-secondary">
              The skills marketplace feature is currently disabled for your
              organization. Contact your administrator to enable this feature.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const handleInstall = async (skillName: string) => {
    setActionError(null);
    try {
      await installSkill({ skillName }).unwrap();
      refetchInstalled();
    } catch (error) {
      const message = getErrorMessage(error);
      setActionError(`Failed to install "${skillName}": ${message}`);
      console.error("Failed to install skill:", error);
    }
  };

  const handleUninstall = async (skillName: string) => {
    setActionError(null);
    try {
      await uninstallSkill(skillName).unwrap();
      refetchInstalled();
    } catch (error) {
      const message = getErrorMessage(error);
      setActionError(`Failed to uninstall "${skillName}": ${message}`);
      console.error("Failed to uninstall skill:", error);
    }
  };

  const handleApplyUpdates = async () => {
    setActionError(null);
    try {
      await applyUpdates().unwrap();
      refetchInstalled();
      refetchUpdates();
    } catch (error) {
      const message = getErrorMessage(error);
      setActionError(`Failed to apply updates: ${message}`);
      console.error("Failed to apply updates:", error);
    }
  };

  const handleRefresh = () => {
    setActionError(null); // Clear errors on refresh
    if (activeTab === "browse") refetchMarketplace();
    else if (activeTab === "installed") refetchInstalled();
    else refetchUpdates();
  };

  const tabs = [
    {
      id: "browse" as const,
      label: "Browse Marketplace",
      icon: Store,
      count: marketplaceData?.total || 0,
    },
    {
      id: "installed" as const,
      label: "Installed",
      icon: HardDrive,
      count: installedData?.count || 0,
    },
    {
      id: "updates" as const,
      label: "Updates",
      icon: ArrowUpCircle,
      count: updatesData?.length || 0,
    },
  ];

  const isLoading =
    activeTab === "browse"
      ? isLoadingMarketplace
      : activeTab === "installed"
        ? isLoadingInstalled
        : isLoadingUpdates;

  return (
    <div className="flex flex-col h-full bg-surface-primary">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
        <div className="flex items-center gap-3">
          <Package className="w-6 h-6 text-accent-primary" />
          <h1 className="text-xl font-semibold text-text-primary">
            Skills Marketplace
          </h1>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary rounded-md transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-6 py-2 border-b border-border-primary bg-surface-secondary/50">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab.id
                ? "bg-accent-primary/10 text-accent-primary"
                : "text-text-secondary hover:text-text-primary hover:bg-surface-secondary"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.count > 0 && (
              <span className="px-1.5 py-0.5 text-xs bg-surface-tertiary rounded-full">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Search and Filters (Browse tab only) */}
      {activeTab === "browse" && (
        <div className="flex items-center gap-4 px-6 py-3 border-b border-border-primary">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-tertiary" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills..."
              className="w-full pl-9 pr-4 py-2 text-sm bg-surface-secondary border border-border-primary rounded-md text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary"
            />
          </div>

          {availableTags.length > 0 && (
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-text-tertiary" />
              <div className="flex gap-1 flex-wrap">
                {availableTags.slice(0, 5).map((tag) => (
                  <button
                    key={tag}
                    onClick={() =>
                      setSelectedTags((prev) =>
                        prev.includes(tag)
                          ? prev.filter((t) => t !== tag)
                          : [...prev, tag],
                      )
                    }
                    className={`px-2 py-1 text-xs rounded-full transition-colors ${
                      selectedTags.includes(tag)
                        ? "bg-accent-primary text-white"
                        : "bg-surface-tertiary text-text-secondary hover:bg-surface-quaternary"
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error Banner */}
      {actionError && (
        <div className="mx-6 mt-4 p-4 bg-semantic-error/10 border border-semantic-error/30 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-semantic-error flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-semantic-error font-medium">
              Action Failed
            </p>
            <p className="text-sm text-text-secondary mt-1">{actionError}</p>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-text-tertiary hover:text-text-primary transition-colors"
            aria-label="Dismiss error"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
          </div>
        ) : activeTab === "browse" ? (
          <BrowseContent
            skills={filteredSkills}
            installedSkills={installedData?.skills || []}
            onInstall={handleInstall}
            isInstalling={isInstalling}
            error={marketplaceError}
          />
        ) : activeTab === "installed" ? (
          <InstalledContent
            installedSkills={installedData?.skills || []}
            onUninstall={handleUninstall}
            isUninstalling={isUninstalling}
          />
        ) : (
          <UpdatesContent
            updates={updatesData || []}
            onApplyAll={handleApplyUpdates}
            isApplying={isApplyingUpdates}
          />
        )}
      </div>
    </div>
  );
}

// Browse Tab Content
function BrowseContent({
  skills,
  installedSkills,
  onInstall,
  isInstalling,
  error,
}: {
  skills: SkillMetadata[];
  installedSkills: string[];
  onInstall: (name: string) => void;
  isInstalling: boolean;
  error: unknown;
}) {
  if (error) {
    // Check if it's an authorization error
    const errorObj = error as Record<string, unknown>;
    const is403 = errorObj?.status === 403;
    const errorMessage = getErrorMessage(error);

    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-secondary">
        <AlertCircle className="w-12 h-12 text-semantic-error mb-4" />
        <p className="text-lg font-medium">
          {is403 ? "Access Denied" : "Failed to load skills"}
        </p>
        <p className="text-sm text-center max-w-md">
          {is403 ? errorMessage : "Please check your connection and try again."}
        </p>
      </div>
    );
  }

  if (skills.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-secondary">
        <Package className="w-12 h-12 text-text-tertiary mb-4" />
        <p className="text-lg font-medium">No skills found</p>
        <p className="text-sm">Try adjusting your search or filters.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {skills.map((skill) => (
        <SkillCard
          key={skill.name}
          skill={skill}
          isInstalled={installedSkills.includes(skill.name)}
          onInstall={() => onInstall(skill.name)}
          isInstalling={isInstalling}
        />
      ))}
    </div>
  );
}

// Installed Tab Content
function InstalledContent({
  installedSkills,
  onUninstall,
  isUninstalling,
}: {
  installedSkills: string[];
  onUninstall: (name: string) => void;
  isUninstalling: boolean;
}) {
  if (installedSkills.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-secondary">
        <HardDrive className="w-12 h-12 text-text-tertiary mb-4" />
        <p className="text-lg font-medium">No skills installed</p>
        <p className="text-sm">
          Browse the marketplace to discover and install skills.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {installedSkills.map((skillName) => (
        <div
          key={skillName}
          className="flex items-center justify-between p-4 bg-surface-secondary rounded-lg border border-border-primary"
        >
          <div className="flex items-center gap-3">
            <Package className="w-5 h-5 text-accent-primary" />
            <span className="font-medium text-text-primary">{skillName}</span>
            <CheckCircle className="w-4 h-4 text-semantic-success" />
          </div>
          <button
            onClick={() => onUninstall(skillName)}
            disabled={isUninstalling}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-semantic-error hover:bg-semantic-error/10 rounded-md transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            Uninstall
          </button>
        </div>
      ))}
    </div>
  );
}

// Updates Tab Content
function UpdatesContent({
  updates,
  onApplyAll,
  isApplying,
}: {
  updates: unknown[];
  onApplyAll: () => void;
  isApplying: boolean;
}) {
  if (updates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-secondary">
        <CheckCircle className="w-12 h-12 text-semantic-success mb-4" />
        <p className="text-lg font-medium">All skills are up to date</p>
        <p className="text-sm">No updates available at this time.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-text-secondary">
          {updates.length} update(s) available
        </p>
        <button
          onClick={onApplyAll}
          disabled={isApplying}
          className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-white rounded-md hover:bg-accent-primary/90 transition-colors disabled:opacity-50"
        >
          {isApplying ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ArrowUpCircle className="w-4 h-4" />
          )}
          Apply All Updates
        </button>
      </div>
    </div>
  );
}

// Skill Card Component
function SkillCard({
  skill,
  isInstalled,
  onInstall,
  isInstalling,
}: {
  skill: SkillMetadata;
  isInstalled: boolean;
  onInstall: () => void;
  isInstalling: boolean;
}) {
  return (
    <div className="flex flex-col p-4 bg-surface-secondary rounded-lg border border-border-primary hover:border-accent-primary/50 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Package className="w-5 h-5 text-accent-primary" />
          <h3 className="font-medium text-text-primary">{skill.name}</h3>
        </div>
        <span className="text-xs text-text-tertiary px-2 py-0.5 bg-surface-tertiary rounded">
          v{skill.version}
        </span>
      </div>

      <p className="text-sm text-text-secondary mb-3 line-clamp-2">
        {skill.description || "No description available"}
      </p>

      {skill.tags && skill.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {skill.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-accent-primary/10 text-accent-primary rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto pt-3 border-t border-border-primary">
        {isInstalled ? (
          <div className="flex items-center gap-2 text-semantic-success">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm">Installed</span>
          </div>
        ) : (
          <button
            onClick={onInstall}
            disabled={isInstalling}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-accent-primary text-white rounded-md hover:bg-accent-primary/90 transition-colors disabled:opacity-50"
          >
            {isInstalling ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Install
          </button>
        )}
      </div>
    </div>
  );
}

export default SkillsPage;
