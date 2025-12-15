import { useState } from "react";
import { useDiscoverContracts } from "../../hooks/useDiscoverContracts";
import type { ContractResponse, ThreadSafety, EvidencePolicy } from "../../api/types";

interface DetailPanelProps {
  node: {
    id: string;
    data: {
      label: string;
      type: string;
      role: string;
      location: string;
      args?: string[];
      config?: Record<string, any>;
      type_location?: { file_path: string; line: number };
      creation_location?: { file_path: string; line: number };
      incoming_connections?: Array<{
        from_name: string;
        method: string;
        location: { file_path: string; line: number };
      }>;
      outgoing_connections?: Array<{
        to_name: string;
        method: string;
        location: { file_path: string; line: number };
      }>;
    };
  } | null;
  edge: {
    id: string;
    source: string;
    target: string;
    label?: string;
    data?: {
      source_name?: string;
      target_name?: string;
      source_location?: { file_path: string; line: number };
    };
  } | null;
  onClose: () => void;
}

type TabType = "instance" | "type";

// ─────────────────────────────────────────────────────────────
// Contract Section Component
// ─────────────────────────────────────────────────────────────

interface ContractSectionProps {
  filePath?: string;
  symbolLine?: number;
}

function ContractSection({ filePath, symbolLine }: ContractSectionProps): JSX.Element {
  const { data, isLoading, error } = useDiscoverContracts({
    filePath: filePath ?? "",
    symbolLine: symbolLine ?? 0,
    enabled: !!filePath && !!symbolLine,
  });

  // No location available
  if (!filePath || !symbolLine) {
    return (
      <div
        style={{
          marginTop: "16px",
          padding: "16px",
          backgroundColor: "#0f172a",
          borderRadius: "6px",
          border: "1px dashed #334155",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "13px", color: "#64748b", fontStyle: "italic" }}>
          No type location available
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div
        style={{
          marginTop: "16px",
          padding: "16px",
          backgroundColor: "#0f172a",
          borderRadius: "6px",
          border: "1px solid #334155",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "13px", color: "#94a3b8" }}>
          Discovering contracts...
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        style={{
          marginTop: "16px",
          padding: "16px",
          backgroundColor: "#0f172a",
          borderRadius: "6px",
          border: "1px solid #ef4444",
        }}
      >
        <div style={{ fontSize: "13px", color: "#ef4444" }}>
          Failed to load contracts
        </div>
        <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>
          {error instanceof Error ? error.message : "Unknown error"}
        </div>
      </div>
    );
  }

  // No contracts found
  const contracts = data?.contracts ?? [];
  if (contracts.length === 0) {
    return (
      <div
        style={{
          marginTop: "16px",
          padding: "16px",
          backgroundColor: "#0f172a",
          borderRadius: "6px",
          border: "1px dashed #334155",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "13px", color: "#64748b", fontStyle: "italic" }}>
          No contracts found
        </div>
        <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>
          Add @aegis-contract block to define contracts
        </div>
      </div>
    );
  }

  // Display contracts
  const contract = contracts[0]; // Show first contract
  return (
    <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
      {/* Contract Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginBottom: "4px",
        }}
      >
        <div style={{ fontSize: "11px", color: "#64748b" }}>CONTRACT</div>
        <ContractConfidenceBadge
          confidence={contract.confidence}
          sourceLevel={contract.source_level}
          needsReview={contract.needs_review}
        />
      </div>

      {/* Thread Safety */}
      {contract.thread_safety && (
        <ContractField label="THREAD SAFETY">
          <ThreadSafetyBadge safety={contract.thread_safety} />
        </ContractField>
      )}

      {/* Lifecycle */}
      {contract.lifecycle && (
        <ContractField label="LIFECYCLE">
          <code style={{ fontSize: "12px", color: "#f1f5f9", fontFamily: "monospace" }}>
            {contract.lifecycle}
          </code>
        </ContractField>
      )}

      {/* Invariants */}
      {(contract.invariants?.length ?? 0) > 0 && (
        <ContractField label="INVARIANTS">
          <ContractList items={contract.invariants!} />
        </ContractField>
      )}

      {/* Preconditions */}
      {(contract.preconditions?.length ?? 0) > 0 && (
        <ContractField label="PRECONDITIONS">
          <ContractList items={contract.preconditions!} />
        </ContractField>
      )}

      {/* Postconditions */}
      {(contract.postconditions?.length ?? 0) > 0 && (
        <ContractField label="POSTCONDITIONS">
          <ContractList items={contract.postconditions!} />
        </ContractField>
      )}

      {/* Errors */}
      {(contract.errors?.length ?? 0) > 0 && (
        <ContractField label="ERRORS">
          <ContractList items={contract.errors!} color="#ef4444" />
        </ContractField>
      )}

      {/* Evidence */}
      {(contract.evidence?.length ?? 0) > 0 && (
        <ContractField label="EVIDENCE">
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {contract.evidence!.map((ev, idx) => (
              <EvidenceItemBadge key={idx} type={ev.type} reference={ev.reference} policy={ev.policy} />
            ))}
          </div>
        </ContractField>
      )}

      {/* Dependencies */}
      {(contract.dependencies?.length ?? 0) > 0 && (
        <ContractField label="DEPENDENCIES">
          <ContractList items={contract.dependencies!} color="#3b82f6" />
        </ContractField>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Contract UI Components
// ─────────────────────────────────────────────────────────────

function ContractField({ label, children }: { label: string; children: React.ReactNode }): JSX.Element {
  return (
    <div>
      <div style={{ fontSize: "10px", color: "#64748b", marginBottom: "4px", letterSpacing: "0.5px" }}>
        {label}
      </div>
      {children}
    </div>
  );
}

function ContractList({ items, color = "#94a3b8" }: { items: string[]; color?: string }): JSX.Element {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      {items.map((item, idx) => (
        <div
          key={idx}
          style={{
            fontSize: "12px",
            fontFamily: "monospace",
            color,
            padding: "4px 8px",
            backgroundColor: "#0f172a",
            borderRadius: "4px",
            border: "1px solid #334155",
          }}
        >
          {item}
        </div>
      ))}
    </div>
  );
}

function ThreadSafetyBadge({ safety }: { safety: ThreadSafety }): JSX.Element {
  const config: Record<ThreadSafety, { label: string; color: string }> = {
    safe: { label: "Thread Safe", color: "#10b981" },
    immutable: { label: "Immutable", color: "#06b6d4" },
    safe_after_start: { label: "Safe After Start", color: "#f59e0b" },
    not_safe: { label: "Not Thread Safe", color: "#ef4444" },
    unknown: { label: "Unknown", color: "#94a3b8" },
  };

  const { label, color } = config[safety] ?? config.unknown;

  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 8px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: 600,
        backgroundColor: `${color}20`,
        color,
        border: `1px solid ${color}`,
      }}
    >
      {label}
    </span>
  );
}

function ContractConfidenceBadge({
  confidence,
  sourceLevel,
  needsReview,
}: {
  confidence: number;
  sourceLevel: number;
  needsReview: boolean;
}): JSX.Element {
  const pct = Math.round(confidence * 100);
  const color = needsReview ? "#f59e0b" : confidence >= 0.8 ? "#10b981" : "#94a3b8";
  const levelLabel = sourceLevel === 1 ? "L1" : sourceLevel === 2 ? "L2" : sourceLevel === 3 ? "L3" : `L${sourceLevel}`;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        padding: "2px 6px",
        borderRadius: "4px",
        fontSize: "10px",
        fontWeight: 500,
        backgroundColor: `${color}20`,
        color,
        border: `1px solid ${color}`,
      }}
      title={`Source: Level ${sourceLevel}, Confidence: ${pct}%${needsReview ? " (needs review)" : ""}`}
    >
      {levelLabel} {pct}%
      {needsReview && " ⚠"}
    </span>
  );
}

function EvidenceItemBadge({
  type,
  reference,
  policy,
}: {
  type: string;
  reference: string;
  policy: EvidencePolicy;
}): JSX.Element {
  const policyColors: Record<EvidencePolicy, string> = {
    required: "#ef4444",
    warning: "#f59e0b",
    optional: "#94a3b8",
  };

  const typeIcons: Record<string, string> = {
    test: "🧪",
    lint: "🔍",
    typecheck: "📝",
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "6px 8px",
        backgroundColor: "#0f172a",
        borderRadius: "4px",
        border: "1px solid #334155",
      }}
    >
      <span style={{ fontSize: "12px" }}>{typeIcons[type] ?? "📋"}</span>
      <span style={{ fontSize: "11px", fontFamily: "monospace", color: "#f1f5f9", flex: 1 }}>
        {reference}
      </span>
      <span
        style={{
          fontSize: "9px",
          fontWeight: 600,
          textTransform: "uppercase",
          color: policyColors[policy],
        }}
      >
        {policy}
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────

export function DetailPanel({ node, edge, onClose }: DetailPanelProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabType>("instance");

  // Helper to format location as clickable link
  const formatLocation = (loc: { file_path: string; line: number } | undefined) => {
    if (!loc) return null;
    return (
      <span
        style={{
          fontSize: "12px",
          fontFamily: "monospace",
          color: "#3b82f6",
          cursor: "pointer",
          textDecoration: "underline",
        }}
        onClick={() => {
          // TODO: Implement file navigation
          console.log("Navigate to:", loc);
        }}
      >
        {loc.file_path}:{loc.line}
      </span>
    );
  };

  // Helper to format role badge
  const getRoleBadge = (role: string) => {
    const roleColors: Record<string, string> = {
      SOURCE: "#10b981",
      PROCESSING: "#3b82f6",
      SINK: "#ef4444",
    };

    return (
      <span
        style={{
          display: "inline-block",
          padding: "4px 8px",
          borderRadius: "4px",
          fontSize: "11px",
          fontWeight: 600,
          textTransform: "uppercase",
          backgroundColor: `${roleColors[role] || "#94a3b8"}20`,
          color: roleColors[role] || "#94a3b8",
          border: `1px solid ${roleColors[role] || "#94a3b8"}`,
        }}
      >
        {role}
      </span>
    );
  };

  return (
    <div
      style={{
        width: "400px",
        borderLeft: "1px solid #334155",
        backgroundColor: "#1e293b",
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      {/* Header with Close Button */}
      <div
        style={{
          padding: "16px",
          borderBottom: "1px solid #334155",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "#f1f5f9" }}>
          {node ? "Instance Details" : "Connection Details"}
        </h3>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#94a3b8",
            cursor: "pointer",
            fontSize: "20px",
            padding: "0",
            lineHeight: "1",
          }}
        >
          ×
        </button>
      </div>

      {/* Tabs (only show for nodes) */}
      {node && (
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid #334155",
            backgroundColor: "#0f172a",
          }}
        >
          <button
            onClick={() => setActiveTab("instance")}
            style={{
              flex: 1,
              padding: "12px",
              border: "none",
              backgroundColor: activeTab === "instance" ? "#1e293b" : "transparent",
              color: activeTab === "instance" ? "#3b82f6" : "#94a3b8",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
              borderBottom: activeTab === "instance" ? "2px solid #3b82f6" : "none",
            }}
          >
            Instance
          </button>
          <button
            onClick={() => setActiveTab("type")}
            style={{
              flex: 1,
              padding: "12px",
              border: "none",
              backgroundColor: activeTab === "type" ? "#1e293b" : "transparent",
              color: activeTab === "type" ? "#3b82f6" : "#94a3b8",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
              borderBottom: activeTab === "type" ? "2px solid #3b82f6" : "none",
            }}
          >
            Type
          </button>
        </div>
      )}

      {/* Content Area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
        }}
      >
        {/* Node Content */}
        {node && activeTab === "instance" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Instance Name */}
            <div>
              <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                INSTANCE NAME
              </div>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "#f1f5f9" }}>
                {node.data.label}
              </div>
            </div>

            {/* Creation Location */}
            {node.data.creation_location && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  CREATED AT
                </div>
                {formatLocation(node.data.creation_location)}
              </div>
            )}

            {/* Constructor Arguments */}
            {node.data.args && node.data.args.length > 0 && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  ARGUMENTS
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                  }}
                >
                  {node.data.args.map((arg, idx) => (
                    <div
                      key={idx}
                      style={{
                        fontSize: "12px",
                        fontFamily: "monospace",
                        color: "#94a3b8",
                        padding: "6px 8px",
                        backgroundColor: "#0f172a",
                        borderRadius: "4px",
                        border: "1px solid #334155",
                      }}
                    >
                      {arg}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Configuration Values */}
            {node.data.config && Object.keys(node.data.config).length > 0 && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  CONFIGURATION
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                  }}
                >
                  {Object.entries(node.data.config).map(([key, value]) => (
                    <div
                      key={key}
                      style={{
                        fontSize: "12px",
                        fontFamily: "monospace",
                        padding: "6px 8px",
                        backgroundColor: "#0f172a",
                        borderRadius: "4px",
                        border: "1px solid #334155",
                      }}
                    >
                      <span style={{ color: "#94a3b8" }}>{key}:</span>{" "}
                      <span style={{ color: "#f1f5f9" }}>
                        {typeof value === "object" ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Incoming Connections */}
            {node.data.incoming_connections && node.data.incoming_connections.length > 0 && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  INCOMING CONNECTIONS
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {node.data.incoming_connections.map((conn, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "8px",
                        backgroundColor: "#0f172a",
                        borderRadius: "4px",
                        border: "1px solid #334155",
                      }}
                    >
                      <div style={{ fontSize: "12px", color: "#f1f5f9", marginBottom: "4px" }}>
                        from <strong>{conn.from_name}</strong> via{" "}
                        <code style={{ color: "#3b82f6" }}>{conn.method}()</code>
                      </div>
                      {formatLocation(conn.location)}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Outgoing Connections */}
            {node.data.outgoing_connections && node.data.outgoing_connections.length > 0 && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  OUTGOING CONNECTIONS
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {node.data.outgoing_connections.map((conn, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "8px",
                        backgroundColor: "#0f172a",
                        borderRadius: "4px",
                        border: "1px solid #334155",
                      }}
                    >
                      <div style={{ fontSize: "12px", color: "#f1f5f9", marginBottom: "4px" }}>
                        to <strong>{conn.to_name}</strong> via{" "}
                        <code style={{ color: "#3b82f6" }}>{conn.method}()</code>
                      </div>
                      {formatLocation(conn.location)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Type Tab Content */}
        {node && activeTab === "type" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Type Symbol Name */}
            <div>
              <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                TYPE SYMBOL
              </div>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "#f1f5f9" }}>
                {node.data.type}
              </div>
            </div>

            {/* Type Location */}
            {node.data.type_location && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  TYPE DEFINITION
                </div>
                {formatLocation(node.data.type_location)}
              </div>
            )}

            {/* Role Badge */}
            <div>
              <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>ROLE</div>
              {getRoleBadge(node.data.role)}
            </div>

            {/* Contract Information (Phase 5) */}
            <ContractSection
              filePath={node.data.type_location?.file_path}
              symbolLine={node.data.type_location?.line}
            />
          </div>
        )}

        {/* Edge Content */}
        {edge && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Connection Info */}
            <div>
              <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>FROM</div>
              <div style={{ fontSize: "14px", fontWeight: 600, color: "#f1f5f9" }}>
                {edge.data?.source_name || edge.source}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>TO</div>
              <div style={{ fontSize: "14px", fontWeight: 600, color: "#f1f5f9" }}>
                {edge.data?.target_name || edge.target}
              </div>
            </div>

            {/* Method */}
            {edge.label && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  METHOD
                </div>
                <div
                  style={{
                    fontSize: "13px",
                    fontFamily: "monospace",
                    color: "#3b82f6",
                    padding: "6px 8px",
                    backgroundColor: "#0f172a",
                    borderRadius: "4px",
                    border: "1px solid #334155",
                  }}
                >
                  {edge.label}()
                </div>
              </div>
            )}

            {/* Location */}
            {edge.data?.source_location && (
              <div>
                <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px" }}>
                  LOCATION
                </div>
                {formatLocation(edge.data.source_location)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
