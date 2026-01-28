/**
 * SkillsPage
 *
 * Skills marketplace page for browsing, installing, and managing skills.
 * Provides tabbed interface for:
 * - Browse: Discover skills from marketplaces
 * - Installed: Manage locally installed skills
 * - Updates: Check for and apply skill updates
 */

import { useState, useMemo, useEffect } from "react";
import {
  Package,
  RefreshCw,
  Search,
  Filter,
  AlertCircle,
  Loader2,
  Store,
  HardDrive,
  ArrowUpCircle,
  Lock,
  Settings,
  X,
} from "lucide-react";
import {
  useListMarketplaceSkillsQuery,
  useInstallSkillMutation,
  useListInstalledSkillsQuery,
  useUninstallSkillMutation,
  useCheckSkillUpdatesQuery,
  useApplySkillUpdatesMutation,
  useListMarketplacesQuery,
  useAddMarketplaceMutation,
  useRemoveMarketplaceMutation,
  useSyncMarketplaceMutation,
  type SkillMetadata,
} from "../api";
import { useFeatureFlags } from "../contexts/FeatureFlagContext";

// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Button } from "@/components/UI/Button";
import { Input } from "@/components/UI/Input";
import { Select } from "@/components/UI/Select";
import {
  SkillDetails,
  InstallDialog,
  UninstallDialog,
  BrowseContent,
  InstalledContent,
  UpdatesContent,
  MarketplaceManager,
  AddMarketplaceDialog,
  RemoveMarketplaceDialog,
} from "@/components/Skills";
import type { AddMarketplaceFormData } from "@/components/Skills";

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
  const [selectedMarketplace, setSelectedMarketplace] = useState("anthropic");
  const [actionError, setActionError] = useState<string | null>(null);
  // Client-side pagination: how many skills to display (incremented by Load More)
  const [visibleCount, setVisibleCount] = useState(12);
  // Modal state management
  const [selectedSkill, setSelectedSkill] = useState<SkillMetadata | null>(
    null,
  );
  const [showDetails, setShowDetails] = useState(false);
  const [showInstallConfirm, setShowInstallConfirm] = useState(false);
  const [showUninstallConfirm, setShowUninstallConfirm] = useState(false);
  const [skillToUninstall, setSkillToUninstall] = useState<string | null>(null);
  // Marketplace management state
  const [showSettings, setShowSettings] = useState(false);
  const [showAddMarketplace, setShowAddMarketplace] = useState(false);
  const [addMarketplaceError, setAddMarketplaceError] = useState<string | null>(
    null,
  );
  const [syncingMarketplace, setSyncingMarketplace] = useState<string | null>(
    null,
  );
  const [showRemoveMarketplace, setShowRemoveMarketplace] = useState(false);
  const [marketplaceToRemove, setMarketplaceToRemove] = useState<string | null>(
    null,
  );
  const [isRemovingMarketplace, setIsRemovingMarketplace] = useState(false);
  // Import cn utility for class merging (STYLE.md Section 2)
  const cn = (...classes: (string | boolean | undefined)[]) =>
    classes.filter(Boolean).join(" ");

  // Feature flag check
  const { isEnabled, isLoading: isFlagsLoading } = useFeatureFlags();
  const isMarketplaceEnabled = isEnabled("skills_marketplace");

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
      marketplace: selectedMarketplace,
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

  // Marketplace management hooks
  const {
    data: marketplacesData,
    isLoading: isLoadingMarketplaces,
    error: marketplacesError,
  } = useListMarketplacesQuery(undefined, { skip: !isMarketplaceEnabled });

  const [addMarketplace, { isLoading: isAddingMarketplace }] =
    useAddMarketplaceMutation();
  const [removeMarketplace] = useRemoveMarketplaceMutation();
  const [syncMarketplace, { isLoading: isSyncingMarketplace }] =
    useSyncMarketplaceMutation();

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

  // Client-side pagination: slice filteredSkills to visibleCount
  const visibleSkills = useMemo(
    () => filteredSkills.slice(0, visibleCount),
    [filteredSkills, visibleCount],
  );

  // Reset pagination when filters change
  useEffect(() => {
    setVisibleCount(12);
  }, [searchQuery, selectedTags, selectedMarketplace]);

  // Extract unique tags for filtering
  const availableTags = useMemo(() => {
    if (!marketplaceData?.skills) return [];
    const tagSet = new Set<string>();
    marketplaceData.skills.forEach((skill) => {
      skill.tags?.forEach((tag) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [marketplaceData?.skills]);

  // Dynamic marketplace options from registered marketplaces
  const marketplaceOptions = useMemo(() => {
    if (!marketplacesData?.marketplaces) {
      // Fallback to default if no marketplaces loaded yet
      return [{ value: "anthropic", label: "Anthropic" }];
    }
    return marketplacesData.marketplaces.map((mp) => ({
      value: mp.name,
      // Capitalize first letter for display
      label: mp.name.charAt(0).toUpperCase() + mp.name.slice(1),
    }));
  }, [marketplacesData?.marketplaces]);

  // Show disabled state if feature is not enabled (after all hooks)
  if (!isFlagsLoading && !isMarketplaceEnabled) {
    return (
      <div
        className="flex flex-col h-full bg-neutral-1"
        data-testid="skills-page-disabled"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-6">
          <div className="flex items-center gap-3">
            <Package className="w-6 h-6 text-neutral-9" />
            <h1 className="text-xl font-semibold text-neutral-12">
              Skills Marketplace
            </h1>
          </div>
        </div>

        {/* Disabled State */}
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center text-center max-w-md px-6">
            <div className="w-16 h-16 rounded-full bg-neutral-3 flex items-center justify-center mb-4">
              <Lock className="w-8 h-8 text-neutral-9" />
            </div>
            <h2 className="text-lg font-semibold text-neutral-12 mb-2">
              Skills Marketplace Disabled
            </h2>
            <p className="text-neutral-11">
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

  // Show uninstall confirmation dialog
  const handleUninstallRequest = (skillName: string) => {
    setSkillToUninstall(skillName);
    setShowUninstallConfirm(true);
  };

  // Actually perform the uninstall after confirmation
  const handleUninstallConfirm = async () => {
    if (!skillToUninstall) return;

    setActionError(null);
    try {
      await uninstallSkill(skillToUninstall).unwrap();
      refetchInstalled();
      setShowUninstallConfirm(false);
      setSkillToUninstall(null);
    } catch (error) {
      const message = getErrorMessage(error);
      setActionError(`Failed to uninstall "${skillToUninstall}": ${message}`);
      console.error("Failed to uninstall skill:", error);
      setShowUninstallConfirm(false);
      setSkillToUninstall(null);
    }
  };

  // Close uninstall dialog
  const handleUninstallCancel = () => {
    setShowUninstallConfirm(false);
    setSkillToUninstall(null);
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

  // Marketplace management handlers
  const handleAddMarketplace = async (data: AddMarketplaceFormData) => {
    setAddMarketplaceError(null);
    try {
      await addMarketplace({
        name: data.name,
        uri: data.uri,
        type: data.type,
        trusted: data.trusted,
        autoSync: data.autoSync,
        requiresApproval: data.requiresApproval,
      }).unwrap();
      setShowAddMarketplace(false);
    } catch (error) {
      const message = getErrorMessage(error);
      setAddMarketplaceError(message);
    }
  };

  // Show remove confirmation dialog
  const handleRemoveMarketplaceRequest = (name: string) => {
    setMarketplaceToRemove(name);
    setShowRemoveMarketplace(true);
  };

  // Actually perform the removal after confirmation
  const handleRemoveMarketplaceConfirm = async () => {
    if (!marketplaceToRemove) return;

    setIsRemovingMarketplace(true);
    try {
      await removeMarketplace(marketplaceToRemove).unwrap();
      setShowRemoveMarketplace(false);
      setMarketplaceToRemove(null);
    } catch (error) {
      const message = getErrorMessage(error);
      setActionError(
        `Failed to remove marketplace "${marketplaceToRemove}": ${message}`,
      );
      setShowRemoveMarketplace(false);
      setMarketplaceToRemove(null);
    } finally {
      setIsRemovingMarketplace(false);
    }
  };

  // Close remove dialog
  const handleRemoveMarketplaceCancel = () => {
    setShowRemoveMarketplace(false);
    setMarketplaceToRemove(null);
  };

  const handleSyncMarketplace = async (name: string) => {
    setSyncingMarketplace(name);
    try {
      await syncMarketplace(name).unwrap();
      refetchMarketplace();
    } catch (error) {
      const message = getErrorMessage(error);
      setActionError(`Failed to sync marketplace "${name}": ${message}`);
    } finally {
      setSyncingMarketplace(null);
    }
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
    <div
      className="flex flex-col h-full bg-neutral-1"
      data-testid="skills-page"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-6">
        <div className="flex items-center gap-3">
          <Package className="w-6 h-6 text-primary-9" />
          <h1 className="text-xl font-semibold text-neutral-12">
            Skills Marketplace
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            className="flex gap-2 focus-visible:ring-2 focus-visible:ring-primary-9"
            onClick={handleRefresh}
            disabled={isLoading}
            data-testid="skills-refresh-button"
          >
            <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
            Refresh
          </Button>
          <Button
            variant="ghost"
            className="flex gap-2 focus-visible:ring-2 focus-visible:ring-primary-9"
            onClick={() => setShowSettings(true)}
            data-testid="skills-settings-button"
            aria-label="Settings"
          >
            <Settings className="w-4 h-4" />
            Settings
          </Button>
        </div>
      </div>
      {/* Tabs */}
      <div
        className="flex items-center gap-1 px-6 py-2 border-b border-neutral-6 bg-neutral-2"
        data-testid="skills-tabs"
      >
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? "secondary" : "ghost"}
            className={cn(
              "flex gap-2 focus-visible:ring-2 focus-visible:ring-primary-9",
              activeTab === tab.id && "bg-neutral-3",
            )}
            onClick={() => setActiveTab(tab.id)}
            data-testid={`skills-tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.count > 0 && (
              <span className="px-1.5 py-0.5 text-xs bg-neutral-4 text-neutral-11 rounded-full">
                {tab.count}
              </span>
            )}
          </Button>
        ))}
      </div>
      {/* Search and Filters (Browse tab only) */}
      {activeTab === "browse" && (
        <div
          className="flex items-center gap-4 px-6 py-3 border-b border-neutral-6"
          data-testid="skills-filters"
        >
          {/* Marketplace Selector */}
          <div className="flex items-center gap-2">
            <Store className="w-4 h-4 text-neutral-9" />
            <Select
              aria-label="Marketplace"
              value={selectedMarketplace}
              onChange={(e) => {
                setSelectedMarketplace(e.target.value);
                refetchMarketplace();
              }}
              size="sm"
              fullWidth={false}
              options={marketplaceOptions}
              data-testid="skills-marketplace-select"
            />
          </div>

          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-9" />
            <Input
              className="pl-9 pr-4 py-2 text-sm bg-neutral-2 border-neutral-6 text-neutral-12 placeholder-neutral-9 focus:ring-2 focus:ring-primary-9/40"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills..."
              data-testid="skills-search-input"
            />
          </div>

          {availableTags.length > 0 && (
            <div
              className="flex items-center gap-2"
              data-testid="skills-tag-filters"
            >
              <Filter className="w-4 h-4 text-neutral-9" />
              <div className="flex gap-1 flex-wrap">
                {availableTags.slice(0, 5).map((tag) => (
                  <Button
                    key={tag}
                    variant={selectedTags.includes(tag) ? "secondary" : "ghost"}
                    size="sm"
                    className={cn(
                      "px-2 py-1 text-xs rounded-full focus-visible:ring-2 focus-visible:ring-primary-9",
                      selectedTags.includes(tag) &&
                        "bg-primary-3 text-primary-11",
                    )}
                    onClick={() =>
                      setSelectedTags((prev) =>
                        prev.includes(tag)
                          ? prev.filter((t) => t !== tag)
                          : [...prev, tag],
                      )
                    }
                    data-testid={`skills-tag-${tag}`}
                  >
                    {tag}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {/* Error Banner */}
      {actionError && (
        <div
          className="mx-6 mt-4 p-4 bg-error-3 border border-error-6 rounded-lg flex items-start gap-3"
          role="alert"
          data-testid="skills-error-banner"
        >
          <AlertCircle className="w-5 h-5 text-error-11 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-error-11 font-medium">Action Failed</p>
            <p className="text-sm text-neutral-11 mt-1">{actionError}</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="text-neutral-9 hover:text-neutral-12 focus-visible:ring-2 focus-visible:ring-primary-9"
            onClick={() => setActionError(null)}
            aria-label="Dismiss error"
            data-testid="skills-error-dismiss"
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
          </Button>
        </div>
      )}
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6" data-testid="skills-content">
        {isLoading ? (
          <div
            className="flex items-center justify-center h-64"
            data-testid="skills-loading"
          >
            <Loader2 className="w-8 h-8 text-primary-9 animate-spin" />
          </div>
        ) : activeTab === "browse" ? (
          <BrowseContent
            skills={visibleSkills}
            installedSkills={installedData?.skills || []}
            onInstall={handleInstall}
            isInstalling={isInstalling}
            error={marketplaceError}
            onRetry={refetchMarketplace}
            total={filteredSkills.length}
            onLoadMore={() => {
              // Client-side pagination: show 12 more skills
              setVisibleCount((prev) => prev + 12);
            }}
            onViewDetails={(skill) => {
              setSelectedSkill(skill);
              setShowDetails(true);
            }}
          />
        ) : activeTab === "installed" ? (
          <InstalledContent
            installedSkills={installedData?.skills || []}
            onUninstall={handleUninstallRequest}
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

      {/* Skill Details Modal */}
      <SkillDetails
        skill={selectedSkill}
        isOpen={showDetails}
        isInstalled={
          selectedSkill
            ? (installedData?.skills || []).includes(selectedSkill.name)
            : false
        }
        isInstalling={isInstalling}
        onClose={() => {
          setShowDetails(false);
          setSelectedSkill(null);
        }}
        onInstall={() => {
          if (selectedSkill) {
            setShowDetails(false);
            setShowInstallConfirm(true);
          }
        }}
      />

      {/* Install Confirmation Dialog */}
      <InstallDialog
        skill={selectedSkill}
        isOpen={showInstallConfirm}
        isInstalling={isInstalling}
        onClose={() => {
          setShowInstallConfirm(false);
          setSelectedSkill(null);
        }}
        onConfirm={async () => {
          if (selectedSkill) {
            await handleInstall(selectedSkill.name);
            setShowInstallConfirm(false);
            setSelectedSkill(null);
          }
        }}
      />

      {/* Uninstall Confirmation Dialog */}
      <UninstallDialog
        skillName={skillToUninstall}
        isOpen={showUninstallConfirm}
        isUninstalling={isUninstalling}
        onClose={handleUninstallCancel}
        onConfirm={handleUninstallConfirm}
      />

      {/* Settings Panel (Marketplace Manager) */}
      {showSettings && (
        <div
          className="fixed inset-0 z-50 flex justify-end"
          onClick={() => setShowSettings(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50" aria-hidden="true" />

          {/* Panel */}
          <div
            className="relative z-10 w-full max-w-md bg-neutral-1 h-full shadow-xl overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Panel Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-6 sticky top-0 bg-neutral-1 z-10">
              <h2 className="text-lg font-semibold text-neutral-12">
                Settings
              </h2>
              <Button
                variant="ghost"
                className="focus-visible:ring-2 focus-visible:ring-primary-9"
                onClick={() => setShowSettings(false)}
                aria-label="Close settings"
                data-testid="skills-settings-close"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Panel Content */}
            <div className="p-6">
              <MarketplaceManager
                marketplaces={marketplacesData?.marketplaces || []}
                onAdd={() => setShowAddMarketplace(true)}
                onRemove={handleRemoveMarketplaceRequest}
                onSync={handleSyncMarketplace}
                isLoading={isLoadingMarketplaces}
                isSyncing={isSyncingMarketplace}
                syncingMarketplace={syncingMarketplace}
                error={
                  marketplacesError ? getErrorMessage(marketplacesError) : null
                }
              />
            </div>
          </div>
        </div>
      )}

      {/* Add Marketplace Dialog */}
      <AddMarketplaceDialog
        isOpen={showAddMarketplace}
        onClose={() => {
          setShowAddMarketplace(false);
          setAddMarketplaceError(null);
        }}
        onSubmit={handleAddMarketplace}
        isSubmitting={isAddingMarketplace}
        error={addMarketplaceError}
      />

      {/* Remove Marketplace Confirmation Dialog */}
      <RemoveMarketplaceDialog
        marketplaceName={marketplaceToRemove}
        isOpen={showRemoveMarketplace}
        isRemoving={isRemovingMarketplace}
        onClose={handleRemoveMarketplaceCancel}
        onConfirm={handleRemoveMarketplaceConfirm}
      />
    </div>
  );
}

export default SkillsPage;
