/**
 * Session History Sidebar
 *
 * Displays list of saved Claude Agent sessions with ability to
 * load, delete, and manage conversation history.
 */

import { useCallback } from "react";
import {
  useSessionHistoryStore,
  SessionSnapshot,
} from "../stores/sessionHistoryStore";

interface SessionHistorySidebarProps {
  onLoadSession: (messages: SessionSnapshot["messages"]) => void;
  onNewSession: () => void;
}

export function SessionHistorySidebar({
  onLoadSession,
  onNewSession,
}: SessionHistorySidebarProps) {
  const {
    sessions,
    currentSessionId,
    sidebarOpen,
    loadSession,
    deleteSession,
    clearAllSessions,
    setCurrentSessionId,
    toggleSidebar,
  } = useSessionHistoryStore();

  const handleLoadSession = useCallback(
    (id: string) => {
      const session = loadSession(id);
      if (session) {
        setCurrentSessionId(id);
        onLoadSession(session.messages);
      }
    },
    [loadSession, setCurrentSessionId, onLoadSession]
  );

  const handleNewSession = useCallback(() => {
    setCurrentSessionId(null);
    onNewSession();
  }, [setCurrentSessionId, onNewSession]);

  const handleDeleteSession = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      if (confirm("Delete this session?")) {
        deleteSession(id);
      }
    },
    [deleteSession]
  );

  const handleClearAll = useCallback(() => {
    if (confirm("Delete all sessions? This cannot be undone.")) {
      clearAllSessions();
      onNewSession();
    }
  }, [clearAllSessions, onNewSession]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } else if (days === 1) {
      return "Yesterday";
    } else if (days < 7) {
      return date.toLocaleDateString([], { weekday: "short" });
    } else {
      return date.toLocaleDateString([], { month: "short", day: "numeric" });
    }
  };

  return (
    <>
      {/* Toggle button */}
      <button
        className="sidebar-toggle"
        onClick={toggleSidebar}
        title={sidebarOpen ? "Close history" : "Open history"}
      >
        {sidebarOpen ? "«" : "»"}
      </button>

      {/* Sidebar */}
      <div className={`session-sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <h3>History</h3>
          <div className="sidebar-actions">
            <button
              className="sidebar-btn new"
              onClick={handleNewSession}
              title="New session"
            >
              + New
            </button>
            {sessions.length > 0 && (
              <button
                className="sidebar-btn clear"
                onClick={handleClearAll}
                title="Clear all"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div className="session-list">
          {sessions.length === 0 ? (
            <div className="empty-history">
              <p>No saved sessions</p>
              <p className="hint">Conversations are auto-saved</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`session-item ${
                  session.id === currentSessionId ? "active" : ""
                }`}
                onClick={() => handleLoadSession(session.id)}
              >
                <div className="session-item-header">
                  <span className="session-title">{session.title}</span>
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDeleteSession(e, session.id)}
                    title="Delete session"
                  >
                    ×
                  </button>
                </div>
                <div className="session-preview">{session.preview}</div>
                <div className="session-meta">
                  <span className="session-date">
                    {formatDate(session.updatedAt)}
                  </span>
                  <span className="session-count">
                    {session.messageCount} msg{session.messageCount !== 1 ? "s" : ""}
                  </span>
                  {session.model && (
                    <span className="session-model">
                      {session.model.replace("claude-", "").split("-")[0]}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <style>{sidebarStyles}</style>
    </>
  );
}

const sidebarStyles = `
/* Toggle button */
.sidebar-toggle {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 48px;
  background: #1e293b;
  border: 1px solid #334155;
  border-left: none;
  border-radius: 0 6px 6px 0;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  z-index: 100;
  transition: all 0.2s;
}

.sidebar-toggle:hover {
  background: #334155;
  color: #e2e8f0;
}

/* Sidebar */
.session-sidebar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 280px;
  background: #111827;
  border-right: 1px solid #1e293b;
  transform: translateX(-100%);
  transition: transform 0.3s ease;
  z-index: 90;
  display: flex;
  flex-direction: column;
}

.session-sidebar.open {
  transform: translateX(0);
}

.sidebar-header {
  padding: 12px 16px;
  border-bottom: 1px solid #1e293b;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
}

.sidebar-actions {
  display: flex;
  gap: 8px;
}

.sidebar-btn {
  padding: 4px 10px;
  font-size: 11px;
  background: transparent;
  border: 1px solid #334155;
  border-radius: 4px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar-btn:hover {
  background: #1e293b;
  color: #e2e8f0;
}

.sidebar-btn.new {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.sidebar-btn.new:hover {
  background: #2563eb;
}

.sidebar-btn.clear {
  color: #ef4444;
  border-color: #ef4444;
}

.sidebar-btn.clear:hover {
  background: rgba(239, 68, 68, 0.1);
}

/* Session list */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-history {
  padding: 24px 16px;
  text-align: center;
  color: #64748b;
}

.empty-history p {
  margin: 0 0 4px;
  font-size: 13px;
}

.empty-history .hint {
  font-size: 11px;
  color: #475569;
}

/* Session item */
.session-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 4px;
}

.session-item:hover {
  background: #1e293b;
}

.session-item.active {
  background: #1e3a5f;
  border: 1px solid #3b82f6;
}

.session-item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.session-title {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
  line-height: 1.3;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  width: 18px;
  height: 18px;
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 16px;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.2s;
  flex-shrink: 0;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.session-preview {
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.session-meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  font-size: 10px;
  color: #475569;
}

.session-model {
  padding: 1px 4px;
  background: #1e293b;
  border-radius: 3px;
}

/* Scrollbar */
.session-list::-webkit-scrollbar {
  width: 6px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 3px;
}

.session-list::-webkit-scrollbar-thumb:hover {
  background: #475569;
}
`;
