/**
 * SessionsPage
 *
 * Session history page showing all chat sessions with search,
 * filtering, and management capabilities.
 */

import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSessionStore } from '../stores/sessionStore';
import {
  Search,
  Plus,
  Trash2,
  MessageSquare,
  Clock,
  ChevronRight,
  Filter,
  Loader2,
} from 'lucide-react';

export function SessionsPage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'recent' | 'name' | 'messages'>('recent');

  const {
    sessions,
    fetchSessions,
    deleteSession,
    createSession,
    loadSession,
    isLoadingSessions,
  } = useSessionStore();

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const filteredSessions = useMemo(() => {
    const filtered = sessions.filter((session) =>
      session.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Sort sessions
    switch (sortBy) {
      case 'name':
        filtered.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'messages':
        filtered.sort((a, b) => (b.messageCount || 0) - (a.messageCount || 0));
        break;
      case 'recent':
      default:
        filtered.sort((a, b) =>
          new Date(b.updatedAt || b.createdAt).getTime() -
          new Date(a.updatedAt || a.createdAt).getTime()
        );
    }

    return filtered;
  }, [sessions, searchQuery, sortBy]);

  const handleCreateSession = async () => {
    const sessionId = await createSession(`Chat Session ${sessions.length + 1}`);
    if (sessionId) {
      navigate('/studio/chat');
    }
  };

  const handleOpenSession = async (sessionId: string) => {
    await loadSession(sessionId);
    navigate('/studio/chat');
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this session?')) {
      await deleteSession(sessionId);
    }
  };

  const formatDate = (date: string | number | Date) => {
    const d = new Date(date);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Sessions
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Manage your chat sessions and conversation history
            </p>
          </div>
          <button
            onClick={handleCreateSession}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus size={20} />
            New Session
          </button>
        </div>
      </header>

      {/* Search and Filter Bar */}
      <div className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search
              size={20}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sessions..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={20} className="text-gray-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="recent">Most Recent</option>
              <option value="name">Name</option>
              <option value="messages">Message Count</option>
            </select>
          </div>
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoadingSessions && sessions.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            {searchQuery ? (
              <>
                <Search size={48} className="mb-4 opacity-50" />
                <p className="text-lg">No sessions found matching "{searchQuery}"</p>
              </>
            ) : (
              <>
                <MessageSquare size={48} className="mb-4 opacity-50" />
                <p className="text-lg">No sessions yet</p>
                <p className="text-sm mt-2">Create a new session to get started</p>
              </>
            )}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredSessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleOpenSession(session.id)}
                className="group p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 cursor-pointer transition-all hover:shadow-md"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                      {session.name}
                    </h3>
                    <div className="flex items-center gap-3 mt-2 text-sm text-gray-500 dark:text-gray-400">
                      <span className="flex items-center gap-1">
                        <MessageSquare size={14} />
                        {session.messageCount || 0} messages
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={14} />
                        {formatDate(session.updatedAt || session.createdAt)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => handleDeleteSession(e, session.id)}
                      className="p-2 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Delete session"
                    >
                      <Trash2 size={16} />
                    </button>
                    <ChevronRight
                      size={20}
                      className="text-gray-400 group-hover:text-blue-500 transition-colors"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default SessionsPage;
