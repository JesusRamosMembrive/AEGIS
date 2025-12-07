import type { OllamaModelInfo } from "../../api/types";

interface OllamaModelListProps {
  models?: OllamaModelInfo[];
  version?: string | null;
  nextInsightRun?: string | null;
  maxModels?: number;
}

function formatRelativeTime(timestamp: string | null | undefined): string {
  if (!timestamp) return "";
  const now = Date.now();
  const time = new Date(timestamp).getTime();
  if (Number.isNaN(time)) return "";

  const diff = now - time;
  if (diff < 0) return "upcoming";

  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatTimeUntil(timestamp: string | null | undefined): string {
  if (!timestamp) return "";
  const now = Date.now();
  const time = new Date(timestamp).getTime();
  if (Number.isNaN(time)) return "";

  const diff = time - now;
  if (diff <= 0) return "now";

  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `in ${minutes}m`;

  const hours = Math.floor(minutes / 60);
  return `in ${hours}h`;
}

export function OllamaModelList({
  models = [],
  version,
  nextInsightRun,
  maxModels = 3,
}: OllamaModelListProps): JSX.Element {
  const displayModels = models.slice(0, maxModels);

  return (
    <div className="ollama-model-list">
      {version && (
        <div className="ollama-model-list__version">
          v{version}
        </div>
      )}
      {displayModels.length > 0 ? (
        <ul className="ollama-model-list__models">
          {displayModels.map((model) => (
            <li key={model.name} className="ollama-model-list__item">
              <span className="ollama-model-list__name">{model.name}</span>
              <span className="ollama-model-list__size">{model.size_human}</span>
              {model.modified_at && (
                <span className="ollama-model-list__time">
                  {formatRelativeTime(model.modified_at)}
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="ollama-model-list__empty">No models loaded</p>
      )}
      {nextInsightRun && (
        <div className="ollama-model-list__next">
          Next insight: {formatTimeUntil(nextInsightRun)}
        </div>
      )}
    </div>
  );
}
