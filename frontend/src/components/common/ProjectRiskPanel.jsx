import { useMemo } from "react";

const RISK_COLORS = {
    Low: "#22c55e",
    Medium: "#f59e0b",
    High: "#f97316",
    Critical: "#ef4444"
};

const RISK_DEFAULT_SCORES = {
    Low: 15,
    Medium: 45,
    High: 70,
    Critical: 90
};

function normalizeRisk(value) {
    const text = String(value || "").trim().toLowerCase();

    return (
        Object.keys(RISK_COLORS).find(
            (level) => level.toLowerCase() === text
        ) || "Unknown"
    );
}

function normalizeScore(value) {
    if (value === null || value === undefined || value === "") {
        return null;
    }

    const numeric = Number(value);

    if (!Number.isFinite(numeric)) {
        return null;
    }

    // Supports scores stored on a 0–1 scale.
    const percentage = numeric <= 1 ? numeric * 100 : numeric;

    return Math.max(0, Math.min(100, percentage));
}

export default function ProjectRiskPanel({
    project = null,
    onGenerateRisk,
    loading = false,
    role = "client"
}) {
    const risk = normalizeRisk(
        project?.current_risk ??
        project?.risk_level ??
        project?.predicted_risk
    );

    const actualScore = normalizeScore(
        project?.dynamic_risk_score ??
        project?.risk_score
    );

    const displayScore =
        actualScore ?? RISK_DEFAULT_SCORES[risk] ?? 0;

    const hasActualScore = actualScore !== null;

    const color = RISK_COLORS[risk] || "#94a3b8";

    const progress = useMemo(() => {
        return {
            background: `conic-gradient(
                ${color} ${displayScore}%,
                #e2e8f0 ${displayScore}% 100%
            )`
        };
    }, [color, displayScore]);

    const canGenerate = String(role || "").toLowerCase() === "manager";

    return (
        <aside className="project-risk-panel">
            <div className="project-risk-panel__header">
                <h3>Project Risk</h3>
                <span className="project-risk-panel__subtitle">
                    Current assessment
                </span>
            </div>

            <div className="project-risk-panel__gauge" style={progress}>
                <div className="project-risk-panel__gauge-inner">
                    <strong style={{ color }}>
                        {risk === "Unknown" ? "N/A" : risk}
                    </strong>

                    <span>
                        {hasActualScore
                            ? `${displayScore.toFixed(1)}%`
                            : "Score unavailable"}
                    </span>
                </div>
            </div>

            <div className="project-risk-panel__details">
                <div>
                    <span>Initial Prediction</span>
                    <strong>
                        {project?.predicted_risk || "Not available"}
                    </strong>
                </div>

                <div>
                    <span>Current Risk</span>
                    <strong style={{ color }}>{risk}</strong>
                </div>

                <div>
                    <span>Risk Trend</span>
                    <strong>
                        {project?.risk_trend || "Not available"}
                    </strong>
                </div>
            </div>

            {canGenerate && onGenerateRisk && (
                <button
                    type="button"
                    className="project-risk-panel__button"
                    onClick={onGenerateRisk}
                    disabled={loading}
                >
                    {loading
                        ? "Calculating Risk..."
                        : "Generate Risk Assessment"}
                </button>
            )}

            <style>{`
                .project-risk-panel {
                    position: sticky;
                    top: 24px;
                    width: 100%;
                    min-width: 0;
                    padding: 24px;
                    border-radius: 18px;
                    background: #fff;
                    border: 1px solid #e2e8f0;
                    box-shadow: 0 8px 30px rgba(15,23,42,.06);
                }

                .project-risk-panel__header h3 {
                    margin: 0 0 6px;
                    font-size: 18px;
                    color: #0f172a;
                }

                .project-risk-panel__subtitle {
                    color: #64748b;
                    font-size: 13px;
                }

                .project-risk-panel__gauge {
                    width: 190px;
                    height: 190px;
                    margin: 28px auto;
                    padding: 17px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .project-risk-panel__gauge-inner {
                    width: 100%;
                    height: 100%;
                    background: #fff;
                    border-radius: 50%;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }

                .project-risk-panel__gauge-inner strong {
                    font-size: 25px;
                }

                .project-risk-panel__gauge-inner span {
                    font-size: 13px;
                    color: #64748b;
                }

                .project-risk-panel__details {
                    display: grid;
                    gap: 15px;
                    margin-bottom: 22px;
                }

                .project-risk-panel__details > div {
                    display: flex;
                    justify-content: space-between;
                    gap: 12px;
                    font-size: 13px;
                }

                .project-risk-panel__details span {
                    color: #64748b;
                }

                .project-risk-panel__details strong {
                    color: #0f172a;
                    text-align: right;
                }

                .project-risk-panel__button {
                    width: 100%;
                    border: none;
                    border-radius: 10px;
                    padding: 13px;
                    background: #2563eb;
                    color: #fff;
                    font-weight: 600;
                    cursor: pointer;
                }

                .project-risk-panel__button:disabled {
                    opacity: .6;
                    cursor: wait;
                }

                @media (max-width: 900px) {
                    .project-risk-panel {
                        position: static;
                    }
                }
            `}</style>
        </aside>
    );
}