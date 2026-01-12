/**
 * OrganizationManager Component
 *
 * Component for managing organizations with CRUD operations.
 */

import { useState, useMemo } from "react";
import { Plus, Edit2, Trash2, Loader2, Search } from "lucide-react";
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
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">
          Organizations
        </h2>
        <Button
          variant="primary"
          className="flex px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          onClick={() => setIsCreateModalOpen(true)}
        >
          <Plus className="w-4 h-4" />
          Create Organization
        </Button>
      </div>
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400 dark:text-neutral-400" />
        <Input
          className="pl-10 pr-4 py-2 text-neutral-900 dark:text-white focus:ring-primary-500"
          placeholder="Search organizations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      {/* Organization List */}
      {filteredOrganizations.length === 0 ? (
        <div className="text-center py-8 text-neutral-500 dark:text-neutral-400">
          No organizations found
        </div>
      ) : (
        <div className="space-y-2">
          {filteredOrganizations.map((org) => (
            <div
              key={org.id}
              data-testid="org-row"
              onClick={() => onSelect(org.id)}
              className={`flex items-center justify-between p-4 rounded-lg border cursor-pointer transition-colors ${
                selectedOrgId === org.id
                  ? "bg-primary-50 dark:bg-primary-900 border-primary-300 dark:border-primary-700"
                  : "bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700"
              }`}
            >
              <div className="flex-1">
                <h3 className="font-medium text-neutral-900 dark:text-white">
                  {org.name}
                </h3>
                <div className="flex items-center gap-4 mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  <span>{org.memberCount} members</span>
                  <span className="px-2 py-0.5 bg-neutral-100 dark:bg-neutral-700 rounded text-xs">
                    {getTierLabel(org.tier)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  className="p-2 text-neutral-500 dark:text-neutral-400 hover:text-primary-600"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEdit(org);
                  }}
                  aria-label="Edit"
                >
                  <Edit2 className="w-4 h-4" />
                </Button>
                <Button
                  className="p-2 text-neutral-500 dark:text-neutral-400 hover:text-error-600"
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
              className="px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
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
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
          >
            Organization Name
          </label>
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-white focus:ring-primary-500"
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
              className="px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg"
              onClick={() => setIsEditModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
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
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
          >
            Organization Name
          </label>
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-white focus:ring-primary-500"
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
              className="px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg"
              onClick={() => setIsDeleteConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              className="px-4 py-2 bg-error-600 text-white rounded-lg hover:bg-error-700"
              onClick={handleDeleteConfirm}
            >
              Confirm
            </Button>
          </>
        }
      >
        <p className="text-neutral-700 dark:text-neutral-300">
          Are you sure you want to delete this organization? This action cannot
          be undone.
        </p>
      </Dialog>
    </div>
  );
}
