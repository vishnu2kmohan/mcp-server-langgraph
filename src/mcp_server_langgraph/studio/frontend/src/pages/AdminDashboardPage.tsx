/**
 * AdminDashboardPage
 *
 * Admin dashboard page wrapping the AdminDashboard component
 * with system health and HEART metrics data.
 * Uses RTK Query for data fetching.
 */

import {
  AdminDashboard,
  SystemHealth,
  HEARTMetrics,
} from "../components/Admin/AdminDashboard";
import type { User } from "../components/Admin/UserManager";
import {
  useGetHealthQuery,
  useGetHeartMetricsQuery,
  useListAdminUsersQuery,
  useUpdateAdminUserMutation,
  useCreateAdminUserMutation,
} from "../api";

/**
 * Map backend HEART aggregate metrics to frontend HEARTMetrics format
 */
function mapHeartMetrics(
  data:
    | {
        nps_score_avg?: number | null;
        satisfaction_avg?: number | null;
        avg_session_duration_ms?: number | null;
        new_users_count?: number;
        avg_return_visits?: number | null;
        task_success_rate?: number | null;
      }
    | undefined,
): HEARTMetrics {
  if (!data) {
    return {
      happiness: 0,
      engagement: 0,
      adoption: 0,
      retention: 0,
      taskSuccess: 0,
    };
  }

  return {
    // Happiness: Use NPS or satisfaction score (scale to 0-100)
    happiness: data.nps_score_avg
      ? Math.round(data.nps_score_avg * 10)
      : data.satisfaction_avg
        ? Math.round(data.satisfaction_avg * 20)
        : 0,
    // Engagement: Derive from session duration (normalize to 0-100)
    engagement: data.avg_session_duration_ms
      ? Math.min(100, Math.round((data.avg_session_duration_ms / 60000) * 10))
      : 0,
    // Adoption: Use new users count (capped at 100)
    adoption: Math.min(100, data.new_users_count ?? 0),
    // Retention: Use average return visits (scale to 0-100)
    retention: data.avg_return_visits
      ? Math.min(100, Math.round(data.avg_return_visits * 10))
      : 0,
    // Task Success: Convert rate to percentage
    taskSuccess: data.task_success_rate
      ? Math.round(data.task_success_rate * 100)
      : 0,
  };
}

export function AdminDashboardPage() {
  // RTK Query hooks
  const {
    data: healthData,
    isLoading: healthLoading,
    refetch: refetchHealth,
  } = useGetHealthQuery();

  const {
    data: heartData,
    isLoading: heartLoading,
    refetch: refetchHeart,
  } = useGetHeartMetricsQuery({ period: "7d" });

  // User management hooks
  const {
    data: usersData,
    isLoading: usersLoading,
    refetch: refetchUsers,
  } = useListAdminUsersQuery({});

  const [updateUser] = useUpdateAdminUserMutation();
  const [createUser] = useCreateAdminUserMutation();

  const isLoading = healthLoading || heartLoading;

  // Map API users to UserManager format
  const users: User[] = (usersData?.items || []).map((user) => ({
    id: user.user_id,
    email: user.email,
    name: user.username,
    roles: user.roles,
    organizationId: "", // Not available from API
    lastLogin: new Date(), // Not available from API
    isActive: user.active,
  }));

  // User management handlers
  const handleUpdateRoles = (userId: string, roles: string[]) => {
    updateUser({ user_id: userId, roles });
  };

  const handleDeactivate = (userId: string) => {
    updateUser({ user_id: userId, active: false });
  };

  const handleActivate = (userId: string) => {
    updateUser({ user_id: userId, active: true });
  };

  const handleInvite = (email: string, roles: string[]) => {
    // Create user with email as username (simplified)
    createUser({
      username: email.split("@")[0],
      email,
      password: "temporary", // In real app, this would trigger email invite
      roles,
    });
  };

  // Map health data to SystemHealth format
  const systemHealth: SystemHealth = {
    status: healthData?.status === "healthy" ? "healthy" : "degraded",
    uptime: healthData?.uptime_seconds
      ? Math.round((healthData.uptime_seconds / 86400) * 100) / 100 // days to percentage
      : 99.9,
    activeUsers: 0, // Not available in health endpoint
    activeSessions: 0, // Not available in health endpoint
    errorRate: 0, // Not available in health endpoint
  };

  // Map HEART metrics
  const heartMetrics = mapHeartMetrics(heartData);

  const handleRefresh = () => {
    refetchHealth();
    refetchHeart();
    refetchUsers();
  };

  return (
    <div className="h-screen overflow-y-auto">
      <AdminDashboard
        systemHealth={systemHealth}
        heartMetrics={heartMetrics}
        isLoading={isLoading}
        onRefresh={handleRefresh}
        users={users}
        usersLoading={usersLoading}
        onUpdateRoles={handleUpdateRoles}
        onDeactivate={handleDeactivate}
        onActivate={handleActivate}
        onInvite={handleInvite}
      />
    </div>
  );
}

export default AdminDashboardPage;
