/**
 * UserManager Component
 *
 * Component for managing users with role assignments.
 */

import { useState, useMemo } from "react";
import { UserPlus, Search, Loader2 } from "lucide-react";
import { Dialog } from "../UI/Dialog";

import { Button, Input, Checkbox } from "@/components/UI";

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
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">
          User Management
        </h2>
        <Button
          variant="primary"
          className="flex px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          onClick={() => setIsInviteModalOpen(true)}
        >
          <UserPlus className="w-4 h-4" />
          Invite User
        </Button>
      </div>
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400 dark:text-neutral-400" />
        <Input
          className="pl-10 pr-4 py-2 text-neutral-900 dark:text-white focus:ring-primary-500"
          placeholder="Search users..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      {/* User List */}
      <div className="space-y-2">
        {filteredUsers.map((user) => (
          <div
            key={user.id}
            className="flex items-center justify-between p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-neutral-900 dark:text-white">
                  {user.name}
                </h3>
                <div
                  data-testid={
                    user.isActive ? "status-active" : "status-inactive"
                  }
                  className={`w-2 h-2 rounded-full ${
                    user.isActive ? "bg-success-500" : "bg-neutral-400"
                  }`}
                />
              </div>
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                {user.email}
              </p>
              <div className="flex items-center gap-2 mt-2">
                {user.roles.map((role) => (
                  <span
                    key={role}
                    className="px-2 py-0.5 bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 rounded text-xs"
                  >
                    {role}
                  </span>
                ))}
              </div>
              <p className="text-xs text-neutral-400 dark:text-neutral-400 mt-1">
                Last login: {formatDate(user.lastLogin)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                className="px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900 rounded"
                onClick={() => handleManageRoles(user)}
                aria-label="Manage roles"
              >
                Manage Roles
              </Button>
              {user.isActive ? (
                <Button
                  variant="danger"
                  className="px-3 py-1.5 text-sm text-error-600 hover:bg-error-50 dark:hover:bg-error-900 rounded"
                  onClick={() => handleDeactivateClick(user.id)}
                  aria-label="Deactivate"
                >
                  Deactivate
                </Button>
              ) : (
                <Button
                  variant="success"
                  className="px-3 py-1.5 text-sm text-success-600 hover:bg-success-50 dark:hover:bg-success-900 rounded"
                  onClick={() => onActivate(user.id)}
                  aria-label="Activate"
                >
                  Activate
                </Button>
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
            <Button
              variant="secondary"
              className="px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg"
              onClick={() => setIsInviteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              onClick={handleInvite}
            >
              Send Invite
            </Button>
          </>
        }
        contentClassName="space-y-4"
      >
        <div>
          <label
            htmlFor="invite-email"
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
          >
            Email
          </label>
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-white focus:ring-primary-500"
            id="invite-email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
          />
        </div>
        <div>
          <span className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            Roles
          </span>
          <div className="space-y-2">
            {AVAILABLE_ROLES.map((role) => (
              <Checkbox
                key={role}
                checked={inviteRoles.includes(role)}
                onChange={() => handleInviteRoleToggle(role)}
                label={role}
                size="sm"
              />
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
            <Button
              variant="secondary"
              className="px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg"
              onClick={() => setIsRoleModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              onClick={handleSaveRoles}
            >
              Save Roles
            </Button>
          </>
        }
        contentClassName="space-y-4"
      >
        <p className="text-neutral-700 dark:text-neutral-300">
          Managing roles for {editingUser?.name}
        </p>
        <div className="space-y-2">
          {AVAILABLE_ROLES.map((role) => (
            <Checkbox
              key={role}
              checked={selectedRoles.includes(role)}
              onChange={() => handleRoleToggle(role)}
              label={role}
              size="sm"
            />
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
            <Button
              variant="secondary"
              className="px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg"
              onClick={() => setIsDeactivateConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              className="px-4 py-2 bg-error-600 text-white rounded-lg hover:bg-error-700"
              onClick={handleDeactivateConfirm}
            >
              Confirm
            </Button>
          </>
        }
      >
        <p className="text-neutral-700 dark:text-neutral-300">
          Are you sure you want to deactivate this user? They will no longer be
          able to access the system.
        </p>
      </Dialog>
    </div>
  );
}
