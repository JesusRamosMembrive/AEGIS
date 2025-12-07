import type { AgentInstallStatus, StageDetectionStatus } from "../../api/types";

interface AgentDonutChartsProps {
  claude?: AgentInstallStatus;
  codex?: AgentInstallStatus;
  gemini?: AgentInstallStatus;
  detection?: StageDetectionStatus;
}

interface MiniDonutProps {
  present: number;
  expected: number;
  label: string;
  missing?: string[];
}

function MiniDonut({ present, expected, label, missing = [] }: MiniDonutProps): JSX.Element {
  const percentage = expected > 0 ? (present / expected) * 100 : 0;
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  // Color based on percentage
  let strokeColor = "#4ade80"; // green
  if (percentage === 0) {
    strokeColor = "#f87171"; // red
  } else if (percentage < 100) {
    strokeColor = "#fbbf24"; // yellow
  }

  const tooltip = missing.length > 0
    ? `Missing: ${missing.join(", ")}`
    : "All files present";

  return (
    <div className="agent-donut" title={tooltip}>
      <svg
        className="agent-donut__svg"
        width="40"
        height="40"
        viewBox="0 0 40 40"
      >
        {/* Background circle */}
        <circle
          cx="20"
          cy="20"
          r={radius}
          fill="none"
          stroke="rgba(148, 163, 184, 0.2)"
          strokeWidth="4"
        />
        {/* Progress circle */}
        <circle
          cx="20"
          cy="20"
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 20 20)"
          style={{ transition: "stroke-dashoffset 0.3s ease" }}
        />
        {/* Center text */}
        <text
          x="20"
          y="20"
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#e2e8f0"
          fontSize="10"
          fontWeight="500"
        >
          {present}/{expected}
        </text>
      </svg>
      <span className="agent-donut__label">{label}</span>
    </div>
  );
}

function formatNumber(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return value.toString();
}

export function AgentDonutCharts({
  claude,
  codex,
  gemini,
  detection,
}: AgentDonutChartsProps): JSX.Element {
  const claudePresent = claude?.present?.length ?? 0;
  const claudeExpected = claude?.expected?.length ?? 0;
  const claudeMissing = claude?.missing ?? [];

  const codexPresent = codex?.present?.length ?? 0;
  const codexExpected = codex?.expected?.length ?? 0;
  const codexMissing = codex?.missing ?? [];

  const geminiPresent = gemini?.present?.length ?? 0;
  const geminiExpected = gemini?.expected?.length ?? 0;
  const geminiMissing = gemini?.missing ?? [];

  const stage = detection?.recommended_stage;
  const confidence = detection?.confidence?.toUpperCase();
  const loc = detection?.metrics?.lines_of_code as number | undefined;

  return (
    <div className="agent-donuts">
      <div className="agent-donuts__charts">
        <MiniDonut
          present={claudePresent}
          expected={claudeExpected}
          label="Claude"
          missing={claudeMissing}
        />
        <MiniDonut
          present={codexPresent}
          expected={codexExpected}
          label="Codex"
          missing={codexMissing}
        />
        <MiniDonut
          present={geminiPresent}
          expected={geminiExpected}
          label="Gemini"
          missing={geminiMissing}
        />
      </div>
      {(stage || confidence || loc) && (
        <div className="agent-donuts__footer">
          {stage && <span>Stage {stage}</span>}
          {confidence && <span>{confidence}</span>}
          {loc && <span>{formatNumber(loc)} LOC</span>}
        </div>
      )}
    </div>
  );
}
