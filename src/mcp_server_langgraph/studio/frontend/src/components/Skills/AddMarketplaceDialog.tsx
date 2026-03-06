/**
 * AddMarketplaceDialog Component
 *
 * Dialog for adding a new skill marketplace.
 * Includes form for name, URI, type, and options.
 *
 * Following STYLE.md conventions:
 * - Radix 1-12 color scale
 * - Focus-visible rings for keyboard navigation
 * - UI Button component for consistent styling
 */

import { useState, useEffect, useCallback } from "react";
import { Loader2, X } from "lucide-react";
import { Button, Input, Select, Checkbox } from "@/components/UI";
import type { MarketplaceType } from "../../types/skills";

// =============================================================================
// Types
// =============================================================================

export interface AddMarketplaceFormData {
  name: string;
  uri: string;
  type: MarketplaceType;
  trusted: boolean;
  autoSync: boolean;
  requiresApproval: boolean;
}

export interface AddMarketplaceDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback when dialog closes */
  onClose: () => void;
  /** Callback when form is submitted */
  onSubmit: (data: AddMarketplaceFormData) => void;
  /** Loading state for submission */
  isSubmitting?: boolean;
  /** Error message to display */
  error?: string | null;
}

// =============================================================================
// Styles
// =============================================================================

const labelStyles = "block text-sm font-medium text-neutral-12 mb-1.5";

// =============================================================================
// Component
// =============================================================================

const initialFormState: AddMarketplaceFormData = {
  name: "",
  uri: "",
  type: "github",
  trusted: false,
  autoSync: false,
  requiresApproval: true,
};

export function AddMarketplaceDialog({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting = false,
  error = null,
}: AddMarketplaceDialogProps) {
  const [formData, setFormData] =
    useState<AddMarketplaceFormData>(initialFormState);
  const [errors, setErrors] = useState<{ name?: string; uri?: string }>({});

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (!isOpen) {
      setFormData(initialFormState);
      setErrors({});
    }
  }, [isOpen]);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleInputChange = useCallback(
    (field: keyof AddMarketplaceFormData, value: string | boolean) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
      // Clear error when user starts typing
      if (typeof value === "string" && errors[field as "name" | "uri"]) {
        setErrors((prev) => ({ ...prev, [field]: undefined }));
      }
    },
    [errors],
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();

      // Validate
      const newErrors: { name?: string; uri?: string } = {};
      if (!formData.name.trim()) {
        newErrors.name = "Name is required";
      }
      if (!formData.uri.trim()) {
        newErrors.uri = "URI is required";
      }

      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors);
        return;
      }

      onSubmit(formData);
    },
    [formData, onSubmit],
  );

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-overlay-6" aria-hidden="true" />

      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-marketplace-title"
        data-testid="add-marketplace-dialog"
        className="relative z-10 w-full max-w-md rounded-xl bg-neutral-1 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <h2
            id="add-marketplace-title"
            className="text-lg font-semibold text-neutral-12"
          >
            Add Marketplace
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        {/* Error alert */}
        {error && (
          <div
            role="alert"
            className="mb-4 rounded-lg border border-error-6 bg-error-2 p-3 text-sm text-error-11"
          >
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label htmlFor="marketplace-name" className={labelStyles}>
              Name
            </label>
            <Input
              id="marketplace-name"
              type="text"
              variant={errors.name ? "error" : "default"}
              placeholder="my-marketplace"
              value={formData.name}
              onChange={(e) => handleInputChange("name", e.target.value)}
              disabled={isSubmitting}
              fullWidth
            />
            {errors.name && (
              <p className="mt-1 text-xs text-error-11">{errors.name}</p>
            )}
          </div>

          {/* URI */}
          <div>
            <label htmlFor="marketplace-uri" className={labelStyles}>
              URI
            </label>
            <Input
              id="marketplace-uri"
              type="text"
              variant={errors.uri ? "error" : "default"}
              placeholder="https://github.com/org/skills-marketplace"
              value={formData.uri}
              onChange={(e) => handleInputChange("uri", e.target.value)}
              disabled={isSubmitting}
              fullWidth
            />
            {errors.uri && (
              <p className="mt-1 text-xs text-error-11">{errors.uri}</p>
            )}
          </div>

          {/* Type */}
          <div>
            <label htmlFor="marketplace-type" className={labelStyles}>
              Type
            </label>
            <Select
              id="marketplace-type"
              value={formData.type}
              onChange={(e) =>
                handleInputChange("type", e.target.value as MarketplaceType)
              }
              disabled={isSubmitting}
              options={[
                { value: "github", label: "GitHub" },
                { value: "oci", label: "OCI Registry" },
                { value: "registry", label: "Custom Registry" },
              ]}
            />
          </div>

          {/* Options */}
          <div className="space-y-3">
            <Checkbox
              id="marketplace-trusted"
              checked={formData.trusted}
              onChange={(checked) => handleInputChange("trusted", checked)}
              disabled={isSubmitting}
              label="Trusted"
              size="sm"
            />

            <Checkbox
              id="marketplace-auto-sync"
              checked={formData.autoSync}
              onChange={(checked) => handleInputChange("autoSync", checked)}
              disabled={isSubmitting}
              label="Auto-sync"
              size="sm"
            />

            <Checkbox
              id="marketplace-requires-approval"
              checked={formData.requiresApproval}
              onChange={(checked) =>
                handleInputChange("requiresApproval", checked)
              }
              disabled={isSubmitting}
              label="Requires approval"
              size="sm"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2
                    className="h-4 w-4 animate-spin"
                    aria-hidden="true"
                  />
                  Adding
                </>
              ) : (
                "Add"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
