interface CodeMapStatsProps {
  lastFullScan?: string | null;
  capabilities?: Array<{ key: string; available: boolean }>;
}

function formatRelativeTime(timestamp: string | null | undefined): string {
  if (!timestamp) return "Never";
  const now = Date.now();
  const scanTime = new Date(timestamp).getTime();
  if (Number.isNaN(scanTime)) return "Unknown";

  const diff = now - scanTime;
  if (diff < 0) return "Just now";

  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const EXTENSION_MAP: Record<string, string> = {
  python: ".py",
  typescript: ".ts",
  javascript: ".js",
  tsx: ".tsx",
  jsx: ".jsx",
  html: ".html",
};

export function CodeMapStats({
  lastFullScan,
  capabilities = [],
}: CodeMapStatsProps): JSX.Element {
  const activeExtensions = capabilities
    .filter((cap) => cap.available)
    .map((cap) => EXTENSION_MAP[cap.key.toLowerCase()] ?? `.${cap.key.slice(0, 3).toLowerCase()}`)
    .slice(0, 5);

  return (
    <div className="code-map-stats">
      <div className="code-map-stats__row">
        <span className="code-map-stats__label">Last scan:</span>
        <span className="code-map-stats__value">{formatRelativeTime(lastFullScan)}</span>
      </div>
      {activeExtensions.length > 0 && (
        <div className="code-map-stats__row">
          <span className="code-map-stats__label">Extensions:</span>
          <span className="code-map-stats__extensions">
            {activeExtensions.map((ext) => (
              <code key={ext} className="code-map-stats__ext">{ext}</code>
            ))}
          </span>
        </div>
      )}
    </div>
  );
}
