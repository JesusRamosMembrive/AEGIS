/**
 * SymbolDetailsSection - Shows symbol information (class members, docstring)
 * for a type in the instance graph DetailPanel.
 *
 * Phase 7.5: Instance Graph Integration
 */

import { useSymbolDetails } from "../../hooks/useSymbolDetails";
import type { SymbolMember } from "../../api/types";

interface SymbolDetailsSectionProps {
  /** Path to the source file */
  filePath?: string;
  /** Line number where the symbol is defined */
  line?: number;
}

/**
 * Display symbol details including docstring and class members.
 */
export function SymbolDetailsSection({ filePath, line }: SymbolDetailsSectionProps): JSX.Element {
  const { data, isLoading, isError, error } = useSymbolDetails({
    filePath,
    line,
    enabled: !!filePath && typeof line === "number" && line > 0,
  });

  // No location available
  if (!filePath || !line) {
    return (
      <div style={styles.emptyContainer}>
        <div style={styles.emptyText}>No type location available</div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.loadingText}>Loading symbol details...</div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div style={styles.errorContainer}>
        <div style={styles.errorTitle}>Failed to load symbol details</div>
        <div style={styles.errorMessage}>
          {error instanceof Error ? error.message : "Unknown error"}
        </div>
      </div>
    );
  }

  // No data or unknown symbol
  if (!data || data.kind === "unknown") {
    return (
      <div style={styles.emptyContainer}>
        <div style={styles.emptyText}>Symbol not found in index</div>
        <div style={styles.emptyHint}>
          The file may not be indexed yet
        </div>
      </div>
    );
  }

  // Display symbol information
  return (
    <div style={styles.container}>
      {/* Symbol Header */}
      <div style={styles.header}>
        <div style={styles.label}>SYMBOL</div>
        <div style={styles.headerRow}>
          <span style={styles.symbolName}>{data.name}</span>
          <KindBadge kind={data.kind} />
        </div>
      </div>

      {/* Parent class (for methods) */}
      {data.parent && (
        <div style={styles.field}>
          <div style={styles.label}>PARENT CLASS</div>
          <div style={styles.parentName}>{data.parent}</div>
        </div>
      )}

      {/* Docstring */}
      {data.docstring && (
        <div style={styles.field}>
          <div style={styles.label}>DOCSTRING</div>
          <div style={styles.docstring}>{data.docstring}</div>
        </div>
      )}

      {/* Members (for classes) */}
      {data.members && data.members.length > 0 && (
        <div style={styles.field}>
          <div style={styles.label}>
            MEMBERS <span style={styles.count}>({data.members.length})</span>
          </div>
          <div style={styles.membersList}>
            {data.members.map((member, idx) => (
              <MemberItem key={idx} member={member} filePath={filePath} />
            ))}
          </div>
        </div>
      )}

      {/* Metrics (if available) */}
      {data.metrics && Object.keys(data.metrics).length > 0 && (
        <div style={styles.field}>
          <div style={styles.label}>METRICS</div>
          <div style={styles.metricsGrid}>
            {Object.entries(data.metrics).map(([key, value]) => (
              <div key={key} style={styles.metricItem}>
                <span style={styles.metricLabel}>{formatMetricLabel(key)}</span>
                <span style={styles.metricValue}>{formatMetricValue(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Helper Components
// ─────────────────────────────────────────────────────────────

function KindBadge({ kind }: { kind: string }): JSX.Element {
  const kindConfig: Record<string, { label: string; color: string }> = {
    class: { label: "CLASS", color: "#8b5cf6" },
    function: { label: "FUNC", color: "#10b981" },
    method: { label: "METHOD", color: "#3b82f6" },
    unknown: { label: "?", color: "#94a3b8" },
  };

  const config = kindConfig[kind] || kindConfig.unknown;

  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 6px",
        borderRadius: "4px",
        fontSize: "10px",
        fontWeight: 600,
        textTransform: "uppercase",
        backgroundColor: `${config.color}20`,
        color: config.color,
        border: `1px solid ${config.color}`,
      }}
    >
      {config.label}
    </span>
  );
}

interface MemberItemProps {
  member: SymbolMember;
  filePath: string;
}

function MemberItem({ member, filePath }: MemberItemProps): JSX.Element {
  const handleClick = () => {
    // TODO: Implement navigation to member location
    console.log("Navigate to:", filePath, member.lineno);
  };

  const icon = member.kind === "method" || member.kind === "function" ? "fn" : "attr";

  return (
    <div style={styles.memberItem} onClick={handleClick}>
      <div style={styles.memberHeader}>
        <span style={styles.memberIcon}>{icon}</span>
        <span style={styles.memberName}>{member.name}</span>
        <span style={styles.memberLine}>L{member.lineno}</span>
      </div>
      {member.docstring && (
        <div style={styles.memberDocstring}>{truncateDocstring(member.docstring)}</div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Utility Functions
// ─────────────────────────────────────────────────────────────

function truncateDocstring(doc: string, maxLength = 80): string {
  const firstLine = doc.split("\n")[0].trim();
  if (firstLine.length <= maxLength) return firstLine;
  return firstLine.substring(0, maxLength - 3) + "...";
}

function formatMetricLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(value: unknown): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  return String(value);
}

// ─────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  emptyContainer: {
    marginTop: "16px",
    padding: "16px",
    backgroundColor: "#0f172a",
    borderRadius: "6px",
    border: "1px dashed #334155",
    textAlign: "center",
  },
  emptyText: {
    fontSize: "13px",
    color: "#64748b",
    fontStyle: "italic",
  },
  emptyHint: {
    fontSize: "11px",
    color: "#475569",
    marginTop: "4px",
  },
  loadingContainer: {
    marginTop: "16px",
    padding: "16px",
    backgroundColor: "#0f172a",
    borderRadius: "6px",
    border: "1px solid #334155",
    textAlign: "center",
  },
  loadingText: {
    fontSize: "13px",
    color: "#94a3b8",
  },
  errorContainer: {
    marginTop: "16px",
    padding: "16px",
    backgroundColor: "#0f172a",
    borderRadius: "6px",
    border: "1px solid #ef4444",
  },
  errorTitle: {
    fontSize: "13px",
    color: "#ef4444",
  },
  errorMessage: {
    fontSize: "11px",
    color: "#94a3b8",
    marginTop: "4px",
  },
  header: {
    marginBottom: "8px",
  },
  headerRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  symbolName: {
    fontSize: "16px",
    fontWeight: 700,
    color: "#f1f5f9",
  },
  field: {
    marginTop: "8px",
  },
  label: {
    fontSize: "10px",
    color: "#64748b",
    marginBottom: "6px",
    letterSpacing: "0.5px",
  },
  count: {
    color: "#94a3b8",
    fontWeight: 400,
  },
  parentName: {
    fontSize: "13px",
    fontFamily: "monospace",
    color: "#8b5cf6",
  },
  docstring: {
    fontSize: "12px",
    color: "#94a3b8",
    padding: "8px",
    backgroundColor: "#0f172a",
    borderRadius: "4px",
    border: "1px solid #334155",
    whiteSpace: "pre-wrap",
    fontFamily: "monospace",
    lineHeight: 1.5,
  },
  membersList: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    maxHeight: "300px",
    overflowY: "auto",
  },
  memberItem: {
    padding: "8px",
    backgroundColor: "#0f172a",
    borderRadius: "4px",
    border: "1px solid #334155",
    cursor: "pointer",
    transition: "border-color 0.15s ease",
  },
  memberHeader: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  memberIcon: {
    fontSize: "10px",
    fontWeight: 600,
    color: "#3b82f6",
    padding: "2px 4px",
    backgroundColor: "#3b82f620",
    borderRadius: "2px",
    fontFamily: "monospace",
  },
  memberName: {
    fontSize: "12px",
    fontFamily: "monospace",
    color: "#f1f5f9",
    flex: 1,
  },
  memberLine: {
    fontSize: "10px",
    color: "#64748b",
    fontFamily: "monospace",
  },
  memberDocstring: {
    fontSize: "11px",
    color: "#64748b",
    marginTop: "4px",
    marginLeft: "24px",
    fontStyle: "italic",
  },
  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: "8px",
  },
  metricItem: {
    display: "flex",
    flexDirection: "column",
    padding: "8px",
    backgroundColor: "#0f172a",
    borderRadius: "4px",
    border: "1px solid #334155",
  },
  metricLabel: {
    fontSize: "10px",
    color: "#64748b",
    marginBottom: "2px",
  },
  metricValue: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#f1f5f9",
    fontFamily: "monospace",
  },
};
