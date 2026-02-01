/**
 * OrganizationManager Component
 *
 * Component for managing organizations with CRUD operations.
 */

import { useState, useMemo } from "react";
import { useReducedMotion } from "motion/react";
import { Plus, Edit2, Trash2, Loader2, Search } from "lucide-react";
import { cn } from "../../utils/cn";
import { Dialog } from "../UI/Dialog";

import { Button, Input } from "@/components/UI";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  memberCount: number;
  createdAt: Date;
  tier: "free" | "team" | "enterprise";
}

export interface OrganizationFormData {
  name: string;
  slug?: string;
  tier?: Organization["tier"];
}

export interface OrganizationManagerProps {
  organizations: Organization[];
  isLoading: boolean;
  selectedOrgId: string | null;
  onCreate: (data: OrganizationFormData) => void;
  onUpdate: (id: string, data: Partial<OrganizationFormData>) => void;
  onDelete: (id: string) => void;
  onSelect: (id: string) => void;
}

export function OrganizationManager({
  organizations,
  isLoading,
  selectedOrgId,
  onCreate,
  onUpdate,
  onDelete,
  onSelect,
}: OrganizationManagerProps) {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  const [searchQuery, setSearchQuery] = useState("");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null);
  const [deletingOrgId, setDeletingOrgId] = useState<string | null>(null);
  const [formData, setFormData] = useState<OrganizationFormData>({ name: "" });

  const filteredOrganizations = useMemo(() => {
    if (!searchQuery) return organizations;
    const query = searchQuery.toLowerCase();
    return organizations.filter(
      (org) =>
        org.name.toLowerCase().includes(query) ||
        org.slug.toLowerCase().includes(query),
    );
  }, [organizations, searchQuery]);

  const handleCreate = () => {
    onCreate(formData);
    setFormData({ name: "" });
    setIsCreateModalOpen(false);
  };

  const handleEdit = (org: Organization) => {
    setEditingOrg(org);
    setFormData({ name: org.name, slug: org.slug, tier: org.tier });
    setIsEditModalOpen(true);
  };

  const handleUpdate = () => {
    if (editingOrg) {
      onUpdate(editingOrg.id, formData);
      setEditingOrg(null);
      setFormData({ name: "" });
      setIsEditModalOpen(false);
    }
  };

  const handleDeleteClick = (id: string) => {
    setDeletingOrgId(id);
    setIsDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (deletingOrgId) {
      onDelete(deletingOrgId);
      setDeletingOrgId(null);
      setIsDeleteConfirmOpen(false);
    }
  };

  const getTierLabel = (tier: Organization["tier"]) => {
    switch (tier) {
      case "free":
        return "Free";
      case "team":
        return "Team";
      case "enterprise":
        return "Enterprise";
    }
  };

  if (isLoading) {
    return (
      <div
        data-testid="org-loading"
        className="flex items-center justify-center h-full"
      >
        <Loader2
          className={cn(
            "w-8 h-8 text-primary-9",
            !prefersReducedMotion && "animate-spin",
          )}
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-neutral-12">Organizations</h2>
        <Button
          variant="primary"
          className="flex px-4 py-2 bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
          onClick={() => setIsCreateModalOpen(true)}
        >
          <Plus className="w-4 h-4" />
          Create Organization
        </Button>
      </div>
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-9" />
        <Input
          className="pl-10 pr-4 py-2 text-neutral-12 focus:ring-primary-7"
          placeholder="Search organizations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      {/* Organization List */}
      {filteredOrganizations.length === 0 ? (
        <div className="text-center py-8 text-neutral-10">
          No organizations found
        </div>
      ) : (
        <div className="space-y-2">
          {filteredOrganizations.map((org) => (
            <div
              key={org.id}
              data-testid="org-row"
              onClick={() => onSelect(org.id)}
              className={cn(
                "flex items-center justify-between p-4 rounded-lg border cursor-pointer transition-colors",
                selectedOrgId === org.id
                  ? "bg-primary-1 dark:bg-primary-12 border-primary-5 dark:border-primary-11"
                  : "bg-neutral-1 border-neutral-5 hover:bg-neutral-1",
              )}
            >
              <div className="flex-1">
                <h3 className="font-medium text-neutral-12">{org.name}</h3>
                <div className="flex items-center gap-4 mt-1 text-sm text-neutral-10">
                  <span>{org.memberCount} members</span>
                  <span className="px-2 py-0.5 bg-neutral-2 rounded text-xs">
                    {getTierLabel(org.tier)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  className="p-2 text-neutral-10 hover:text-primary-10"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEdit(org);
                  }}
                  aria-label="Edit"
                >
                  <Edit2 className="w-4 h-4" />
                </Button>
                <Button
                  variant="danger"
                  className="p-2 text-neutral-10 hover:text-error-10"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteClick(org.id);
                  }}
                  aria-label="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Create Modal */}
      <Dialog
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Organization"
        footer={
          <>
            <Button
              variant="secondary"
              className="px-4 py-2 text-neutral-11 hover:bg-neutral-2 rounded-lg"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="px-4 py-2 bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
              onClick={handleCreate}
            >
              Create
            </Button>
          </>
        }
      >
        <div>
          <label
            htmlFor="org-name"
            className="block text-sm font-medium text-neutral-11 mb-1"
          >
            Organization Name
          </label>
          <Input
            className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
            id="org-name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>
      </Dialog>
      {/* Edit Modal */}
      <Dialog
        open={isEditModalOpen && !!editingOrg}
        onClose={() => setIsEditModalOpen(false)}
        title="Edit Organization"
        footer={
          <>
            <Button
              variant="secondary"
              className="px-4 py-2 text-neutral-11 hover:bg-neutral-2 rounded-lg"
              onClick={() => setIsEditModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="px-4 py-2 bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
              onClick={handleUpdate}
            >
              Save
            </Button>
          </>
        }
      >
        <div>
          <label
            htmlFor="edit-org-name"
            className="block text-sm font-medium text-neutral-11 mb-1"
          >
            Organization Name
          </label>
          <Input
            className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
            id="edit-org-name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>
      </Dialog>
      {/* Delete Confirmation */}
      <Dialog
        open={isDeleteConfirmOpen}
        onClose={() => setIsDeleteConfirmOpen(false)}
        title="Confirm Delete"
        footer={
          <>
            <Button
              variant="secondary"
              className="px-4 py-2 text-neutral-11 hover:bg-neutral-2 rounded-lg"
              onClick={() => setIsDeleteConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              className="px-4 py-2 bg-error-10 text-neutral-12 rounded-lg hover:bg-error-11"
              onClick={handleDeleteConfirm}
            >
              Confirm
            </Button>
          </>
        }
      >
        <p className="text-neutral-11">
          Are you sure you want to delete this organization? This action cannot
          be undone.
        </p>
      </Dialog>
    </div>
  );
}
