import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

interface ModuleInstanceData {
  label: string;
  type: string;
  role: 'source' | 'processing' | 'sink' | 'unknown';
  location: string;
}

const ROLE_COLORS = {
  source: '#10b981',      // green
  processing: '#3b82f6',  // blue
  sink: '#a855f7',        // purple
  unknown: '#6b7280',     // gray
} as const;

const ROLE_LABELS = {
  source: 'Source',
  processing: 'Processing',
  sink: 'Sink',
  unknown: 'Unknown',
} as const;

export const ModuleInstanceNode = memo(({ data }: NodeProps<ModuleInstanceData>) => {
  const roleColor = ROLE_COLORS[data.role];
  const roleLabel = ROLE_LABELS[data.role];

  return (
    <div
      className="module-instance-node"
      style={{
        padding: '12px 16px',
        borderRadius: '8px',
        border: `2px solid ${roleColor}`,
        backgroundColor: '#1e293b',
        color: '#f1f5f9',
        minWidth: '180px',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: roleColor,
          width: '10px',
          height: '10px',
        }}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ fontWeight: 600, fontSize: '14px', lineHeight: '1.2' }}>
          {data.label}
        </div>

        <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.2' }}>
          {data.type}
        </div>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            fontSize: '11px',
            fontWeight: 500,
            padding: '2px 8px',
            borderRadius: '4px',
            backgroundColor: roleColor,
            color: '#fff',
            width: 'fit-content',
            marginTop: '2px',
          }}
        >
          {roleLabel}
        </div>

        {data.location && (
          <div
            style={{
              fontSize: '10px',
              color: '#64748b',
              marginTop: '2px',
              fontFamily: 'monospace',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={data.location}
          >
            {data.location}
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: roleColor,
          width: '10px',
          height: '10px',
        }}
      />
    </div>
  );
});

ModuleInstanceNode.displayName = 'ModuleInstanceNode';
