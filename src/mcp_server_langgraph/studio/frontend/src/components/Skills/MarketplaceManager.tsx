/**
 * MarketplaceManager Component
 *
 * Displays and manages registered skill marketplaces.
 * Allows adding, removing, and syncing marketplaces.
 *
 * Following STYLE.md conventions:
 * - CVA for button variants
 * - Radix 1-12 color scale
 * - Focus-visible rings for keyboard navigation
 * - Semantic button variants (secondary, danger, primary)
 */

import { cva } from "class-variance-authority";
import { Loader2, Plus, RefreshCw, Trash2, Shield, Zap } from "lucide-react";
import { Button } from "@/components/UI";
import type { MarketplaceInfo } from "../../types/skills";

// =============================================================================
// Types
// =============================================================================

export interface MarketplaceManagerProps {
  /** List of registered marketplaces */
  marketplaces: MarketplaceInfo[];
  /** Callback when Add Marketplace button clicked */
  onAdd: () => void;
  /** Callback when Remove button clicked with marketplace name */
  onRemove: (name: string) => void;
  /** Callback when Sync button clicked with marketplace name */
  onSync: (name: string) => void;
  /** Loading state for initial data fetch */
  isLoading?: boolean;
  /** Syncing state */
  isSyncing?: boolean;
  /** Name of marketplace currently being synced */
  syncingMarketplace?: string | null;
  /** Error message to display */
  error?: string | null;
}

// =============================================================================
// Styles (CVA)
// =============================================================================

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        trusted: "bg-success-3 text-success-11",
        autoSync: "bg-primary-3 text-primary-11",
        requiresApproval: "bg-warning-3 text-warning-11",
      },
    },
  },
);

// =============================================================================
// Component
// =============================================================================

export function MarketplaceManager({
  marketplaces,
  onAdd,
  onRemove,
  onSync,
  isLoading = false,
  isSyncing = false,
  syncingMarketplace = null,
  error = null,
}: MarketplaceManagerProps) {
  // Default marketplace that cannot be removed
  const defaultMarketplace = "anthropic";

  return (
    <div data-testid="marketplace-manager" className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-neutral-12">Marketplaces</h2>
        <Button variant="secondary" className="gap-2" onClick={onAdd}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add Marketplace
        </Button>
      </div>

      {/* Error state */}
      {error && (
        <div
          role="alert"
          className="rounded-lg border border-error-6 bg-error-2 p-3 text-sm text-error-11"
        >
          {error}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-11" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && marketplaces.length === 0 && (
        <div className="rounded-lg border border-neutral-6 bg-neutral-2 p-8 text-center">
          <p className="text-sm text-neutral-11">No marketplaces registered</p>
          <p className="mt-2 text-xs text-neutral-10">
            Add a marketplace to discover and install skills.
          </p>
        </div>
      )}

      {/* Marketplace list */}
      {!isLoading && marketplaces.length > 0 && (
        <ul
          data-testid="marketplace-list"
          role="list"
          className="divide-y divide-neutral-6 rounded-lg border border-neutral-6"
        >
          {marketplaces.map((marketplace) => {
            const isSyncingThis =
              isSyncing && syncingMarketplace === marketplace.name;
            const isDefault = marketplace.name === defaultMarketplace;

            return (
              <li
                key={marketplace.name}
                data-testid={`marketplace-${marketplace.name}`}
                className="flex items-center justify-between gap-4 p-4"
              >
                {/* Marketplace info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-neutral-12">
                      {marketplace.name}
                    </span>
                    {marketplace.trusted && (
                      <span className={badgeVariants({ variant: "trusted" })}>
                        <Shield className="h-3 w-3" aria-hidden="true" />
                        Trusted
                      </span>
                    )}
                    {marketplace.autoSync && (
                      <span className={badgeVariants({ variant: "autoSync" })}>
                        <Zap className="h-3 w-3" aria-hidden="true" />
                        Auto-sync
                      </span>
                    )}
                  </div>
                  <p className="mt-1 truncate text-sm text-neutral-10">
                    {marketplace.uri}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-2"
                    onClick={() => onSync(marketplace.name)}
                    disabled={isSyncingThis}
                    aria-label={
                      isSyncingThis
                        ? `Syncing ${marketplace.name}`
                        : `Sync ${marketplace.name}`
                    }
                  >
                    {isSyncingThis ? (
                      <>
                        <Loader2
                          className="h-4 w-4 animate-spin"
                          aria-hidden="true"
                        />
                        Syncing
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4" aria-hidden="true" />
                        Sync
                      </>
                    )}
                  </Button>

                  {!isDefault && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-2"
                      onClick={() => onRemove(marketplace.name)}
                      aria-label={`Remove ${marketplace.name}`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                      Remove
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
