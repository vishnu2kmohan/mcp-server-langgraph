/**
 * UserManager Component
 *
 * Component for managing users with role assignments.
 */

import { useState, useMemo } from "react";
import { UserPlus, Search, Loader2 } from "lucide-react";
import { Dialog } from "../UI/Dialog";

export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  organizationId: string;
  lastLogin: Date;
  isActive: boolean;
}

export interface UserManagerProps {
  users: User[];
  isLoading: boolean;
  onUpdateRoles: (userId: string, roles: string[]) => void;
  onDeactivate: (userId: string) => void;
  onActivate: (userId: string) => void;
  onInvite: (email: string, roles: string[]) => void;
}

const AVAILABLE_ROLES = ["admin", "developer", "user"];

export function UserManager({
  users,
  isLoading,
  onUpdateRoles,
  onDeactivate,
  onActivate,
  onInvite,
}: UserManagerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [isDeactivateConfirmOpen, setIsDeactivateConfirmOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deactivatingUserId, setDeactivatingUserId] = useState<string | null>(
    null,
  );
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRoles, setInviteRoles] = useState<string[]>([]);

  const filteredUsers = useMemo(() => {
    if (!searchQuery) return users;
    const query = searchQuery.toLowerCase();
    return users.filter(
      (user) =>
        user.name.toLowerCase().includes(query) ||
        user.email.toLowerCase().includes(query),
    );
  }, [users, searchQuery]);

  const handleManageRoles = (user: User) => {
    setEditingUser(user);
    setSelectedRoles([...user.roles]);
    setIsRoleModalOpen(true);
  };

  const handleSaveRoles = () => {
    if (editingUser) {
      onUpdateRoles(editingUser.id, selectedRoles);
      setEditingUser(null);
      setSelectedRoles([]);
      setIsRoleModalOpen(false);
    }
  };

  const handleRoleToggle = (role: string) => {
    setSelectedRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role],
    );
  };

  const handleInviteRoleToggle = (role: string) => {
    setInviteRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role],
    );
  };

  const handleDeactivateClick = (userId: string) => {
    setDeactivatingUserId(userId);
    setIsDeactivateConfirmOpen(true);
  };

  const handleDeactivateConfirm = () => {
    if (deactivatingUserId) {
      onDeactivate(deactivatingUserId);
      setDeactivatingUserId(null);
      setIsDeactivateConfirmOpen(false);
    }
  };

  const handleInvite = () => {
    onInvite(inviteEmail, inviteRoles);
    setInviteEmail("");
    setInviteRoles([]);
    setIsInviteModalOpen(false);
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });
  };

  if (isLoading) {
    return (
      <div
        data-testid="user-loading"
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
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          User Management
        </h2>
        <button
          onClick={() => setIsInviteModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Invite User
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-400" />
        <input
          type="text"
          placeholder="Search users..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* User List */}
      <div className="space-y-2">
        {filteredUsers.map((user) => (
          <div
            key={user.id}
            className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-gray-900 dark:text-white">
                  {user.name}
                </h3>
                <div
                  data-testid={
                    user.isActive ? "status-active" : "status-inactive"
                  }
                  className={`w-2 h-2 rounded-full ${
                    user.isActive ? "bg-success-500" : "bg-gray-400"
                  }`}
                />
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {user.email}
              </p>
              <div className="flex items-center gap-2 mt-2">
                {user.roles.map((role) => (
                  <span
                    key={role}
                    className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs"
                  >
                    {role}
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                Last login: {formatDate(user.lastLogin)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleManageRoles(user)}
                className="px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900 rounded transition-colors"
                aria-label="Manage roles"
              >
                Manage Roles
              </button>
              {user.isActive ? (
                <button
                  onClick={() => handleDeactivateClick(user.id)}
                  className="px-3 py-1.5 text-sm text-error-600 hover:bg-error-50 dark:hover:bg-error-900 rounded transition-colors"
                  aria-label="Deactivate"
                >
                  Deactivate
                </button>
              ) : (
                <button
                  onClick={() => onActivate(user.id)}
                  className="px-3 py-1.5 text-sm text-success-600 hover:bg-success-50 dark:hover:bg-success-900 rounded transition-colors"
                  aria-label="Activate"
                >
                  Activate
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Invite Modal */}
      <Dialog
        open={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        title="Invite User"
        footer={
          <>
            <button
              onClick={() => setIsInviteModalOpen(false)}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleInvite}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Send Invite
            </button>
          </>
        }
        contentClassName="space-y-4"
      >
        <div>
          <label
            htmlFor="invite-email"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Email
          </label>
          <input
            id="invite-email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <span className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Roles
          </span>
          <div className="space-y-2">
            {AVAILABLE_ROLES.map((role) => (
              <label key={role} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={inviteRoles.includes(role)}
                  onChange={() => handleInviteRoleToggle(role)}
                  className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">{role}</span>
              </label>
            ))}
          </div>
        </div>
      </Dialog>

      {/* Role Management Modal */}
      <Dialog
        open={isRoleModalOpen && !!editingUser}
        onClose={() => setIsRoleModalOpen(false)}
        title="Manage Roles"
        footer={
          <>
            <button
              onClick={() => setIsRoleModalOpen(false)}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveRoles}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Save Roles
            </button>
          </>
        }
        contentClassName="space-y-4"
      >
        <p className="text-gray-700 dark:text-gray-300">
          Managing roles for {editingUser?.name}
        </p>
        <div className="space-y-2">
          {AVAILABLE_ROLES.map((role) => (
            <label key={role} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedRoles.includes(role)}
                onChange={() => handleRoleToggle(role)}
                aria-label={role}
                className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-gray-700 dark:text-gray-300">{role}</span>
            </label>
          ))}
        </div>
      </Dialog>

      {/* Deactivate Confirmation */}
      <Dialog
        open={isDeactivateConfirmOpen}
        onClose={() => setIsDeactivateConfirmOpen(false)}
        title="Confirm Deactivation"
        footer={
          <>
            <button
              onClick={() => setIsDeactivateConfirmOpen(false)}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleDeactivateConfirm}
              className="px-4 py-2 bg-error-600 text-white rounded-lg hover:bg-error-700"
            >
              Confirm
            </button>
          </>
        }
      >
        <p className="text-gray-700 dark:text-gray-300">
          Are you sure you want to deactivate this user? They will no longer be
          able to access the system.
        </p>
      </Dialog>
    </div>
  );
}
