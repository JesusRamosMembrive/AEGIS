import { useState, useMemo } from "react";

import { useInstanceGraphQuery } from "../hooks/useInstanceGraphQuery";
import { ArchitectureGraph } from "./instance-graph/ArchitectureGraph";
import { DirectoryBrowserModal } from "./settings/DirectoryBrowserModal";

export function InstanceGraphView(): JSX.Element {
  const [projectPath, setProjectPath] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [isBrowseModalOpen, setIsBrowseModalOpen] = useState(false);

  const query = useInstanceGraphQuery({
    projectPath,
    enabled: !!projectPath,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setProjectPath(inputValue.trim());
  };

  const handleBrowseSelect = (path: string) => {
    setInputValue(path);
    setProjectPath(path);
  };

  const nodes = useMemo(() => query.data?.nodes || [], [query.data?.nodes]);
  const edges = useMemo(() => query.data?.edges || [], [query.data?.edges]);
  const metadata = query.data?.metadata;

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId),
    [nodes, selectedNodeId]
  );

  const selectedEdge = useMemo(
    () => edges.find((e) => e.id === selectedEdgeId),
    [edges, selectedEdgeId]
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 200px)",
        minHeight: "500px",
        backgroundColor: "#0f172a",
        color: "#f1f5f9",
      }}
    >
      {/* Header Controls */}
      <div
        style={{
          padding: "16px 24px",
          borderBottom: "1px solid #334155",
          backgroundColor: "#1e293b",
        }}
      >
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <label htmlFor="project-path" style={{ fontSize: "14px", fontWeight: 500 }}>
            Project Path:
          </label>
          <input
            id="project-path"
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="/path/to/project or module.py"
            style={{
              flex: 1,
              padding: "8px 12px",
              borderRadius: "6px",
              border: "1px solid #334155",
              backgroundColor: "#0f172a",
              color: "#f1f5f9",
              fontSize: "14px",
            }}
          />
          <button
            type="button"
            onClick={() => setIsBrowseModalOpen(true)}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              border: "1px solid #334155",
              backgroundColor: "#1e293b",
              color: "#f1f5f9",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Browse
          </button>
          <button
            type="submit"
            disabled={query.isFetching}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              border: "none",
              backgroundColor: "#3b82f6",
              color: "#fff",
              fontSize: "14px",
              fontWeight: 500,
              cursor: query.isFetching ? "not-allowed" : "pointer",
              opacity: query.isFetching ? 0.6 : 1,
            }}
          >
            {query.isFetching ? "Loading..." : "Analyze"}
          </button>
        </form>

        {/* Stats Panel */}
        {metadata && !query.isLoading && !query.isError && (
          <div
            style={{
              display: "flex",
              gap: "24px",
              marginTop: "12px",
              padding: "12px",
              backgroundColor: "#0f172a",
              borderRadius: "6px",
              border: "1px solid #334155",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                Source File
              </span>
              <strong style={{ fontSize: "14px" }}>{metadata.source_file}</strong>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                Function
              </span>
              <strong style={{ fontSize: "14px" }}>{metadata.function_name}</strong>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                Nodes
              </span>
              <strong style={{ fontSize: "14px", color: "#3b82f6" }}>
                {metadata.node_count}
              </strong>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                Edges
              </span>
              <strong style={{ fontSize: "14px", color: "#a855f7" }}>
                {metadata.edge_count}
              </strong>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: "flex", position: "relative", minHeight: 0 }}>
        {/* Graph Canvas */}
        <div style={{ flex: 1, position: "relative", height: "100%" }}>
          {query.isLoading && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                fontSize: "16px",
                color: "#94a3b8",
              }}
            >
              Loading instance graph...
            </div>
          )}

          {query.isError && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div style={{ fontSize: "16px", color: "#ef4444", fontWeight: 500 }}>
                Error loading instance graph
              </div>
              <div style={{ fontSize: "14px", color: "#94a3b8" }}>
                {query.error?.message || "Unknown error"}
              </div>
            </div>
          )}

          {!query.isLoading && !query.isError && nodes.length === 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div style={{ fontSize: "16px", color: "#94a3b8" }}>
                {projectPath
                  ? "No instance graph data found"
                  : "Enter a project path to analyze"}
              </div>
            </div>
          )}

          {!query.isLoading && !query.isError && nodes.length > 0 && (
            <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
              <ArchitectureGraph
                nodes={nodes}
                edges={edges}
                onNodeSelect={setSelectedNodeId}
                onEdgeSelect={setSelectedEdgeId}
              />
            </div>
          )}
        </div>

        {/* Selection Details Panel */}
        {(selectedNode || selectedEdge) && (
          <div
            style={{
              width: "300px",
              borderLeft: "1px solid #334155",
              backgroundColor: "#1e293b",
              padding: "16px",
              overflowY: "auto",
            }}
          >
            {selectedNode && (
              <>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#94a3b8",
                    textTransform: "uppercase",
                    marginBottom: "8px",
                  }}
                >
                  Node Details
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>
                      Name
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 500 }}>
                      {selectedNode.data.label}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>
                      Type
                    </div>
                    <div style={{ fontSize: "14px" }}>{selectedNode.data.type}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>
                      Role
                    </div>
                    <div style={{ fontSize: "14px", textTransform: "capitalize" }}>
                      {selectedNode.data.role}
                    </div>
                  </div>
                  {selectedNode.data.location && (
                    <div>
                      <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>
                        Location
                      </div>
                      <div
                        style={{
                          fontSize: "12px",
                          fontFamily: "monospace",
                          wordBreak: "break-all",
                          color: "#94a3b8",
                        }}
                      >
                        {selectedNode.data.location}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}

            {selectedEdge && (
              <>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#94a3b8",
                    textTransform: "uppercase",
                    marginBottom: "8px",
                  }}
                >
                  Edge Details
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>
                      From
                    </div>
                    <div style={{ fontSize: "14px" }}>{selectedEdge.source}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>
                      To
                    </div>
                    <div style={{ fontSize: "14px" }}>{selectedEdge.target}</div>
                  </div>
                  {selectedEdge.label && (
                    <div>
                      <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>
                        Method
                      </div>
                      <div
                        style={{
                          fontSize: "14px",
                          fontFamily: "monospace",
                          color: "#94a3b8",
                        }}
                      >
                        {selectedEdge.label}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Directory Browser Modal */}
      <DirectoryBrowserModal
        isOpen={isBrowseModalOpen}
        currentPath={inputValue || "/home"}
        onClose={() => setIsBrowseModalOpen(false)}
        onSelect={handleBrowseSelect}
      />
    </div>
  );
}
