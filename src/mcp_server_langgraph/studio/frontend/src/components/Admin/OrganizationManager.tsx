/**
 * OrganizationManager Component
 *
 * Component for managing organizations with CRUD operations.
 */

import { useState, useMemo } from "react";
import { Plus, Edit2, Trash2, Loader2, Search } from "lucide-react";
import { Dialog } from "../UI/Dialog";

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
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Organizations
        </h2>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Organization
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search organizations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Organization List */}
      {filteredOrganizations.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
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
                  ? "bg-blue-50 dark:bg-blue-900 border-blue-300 dark:border-blue-700"
                  : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750"
              }`}
            >
              <div className="flex-1">
                <h3 className="font-medium text-gray-900 dark:text-white">
                  {org.name}
                </h3>
                <div className="flex items-center gap-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
                  <span>{org.memberCount} members</span>
                  <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                    {getTierLabel(org.tier)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEdit(org);
                  }}
                  className="p-2 text-gray-500 hover:text-blue-600 transition-colors"
                  aria-label="Edit"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteClick(org.id);
                  }}
                  className="p-2 text-gray-500 hover:text-red-600 transition-colors"
                  aria-label="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
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
            <button
              onClick={() => setIsCreateModalOpen(false)}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Create
            </button>
          </>
        }
      >
        <div>
          <label
            htmlFor="org-name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Organization Name
          </label>
          <input
            id="org-name"
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            <button
              onClick={() => setIsEditModalOpen(false)}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleUpdate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Save
            </button>
          </>
        }
      >
        <div>
          <label
            htmlFor="edit-org-name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Organization Name
          </label>
          <input
            id="edit-org-name"
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            <button
              onClick={() => setIsDeleteConfirmOpen(false)}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleDeleteConfirm}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Confirm
            </button>
          </>
        }
      >
        <p className="text-gray-700 dark:text-gray-300">
          Are you sure you want to delete this organization? This action cannot
          be undone.
        </p>
      </Dialog>
    </div>
  );
}
