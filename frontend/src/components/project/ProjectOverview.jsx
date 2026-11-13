function formatValue(value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    return value;
}

export default function ProjectOverview({
    project = {},
    details = {},
    dynamicRisk,
    teamSize
}) {
    const progress =
        project.project_progress ||
        details.project_progress ||
        "Not Started";

    const budget =
        project.project_budget ??
        details.project_budget ??
        project.project_budget_usd;

    const stats = [
        ["Team Members", teamSize],
        ["Total Tasks", project.total_tasks],
        ["Completed Tasks", project.completed_tasks],
        ["Overdue Tasks", project.overdue_tasks],
        ["Progress Status", progress],
        ["Timeline", `${formatValue(project.timeline_months)} months`],
        ["Estimated Effort", `${formatValue(project.estimated_effort_hours)} hrs`],
        ["Actual Effort", `${formatValue(project.actual_effort_hours)} hrs`]
    ];

    return (
        <section className="project-section">
            <h2>Project Summary</h2>

            <div className="project-stats-grid">
                {stats.map(([label, value]) => (
                    <div className="project-stat" key={label}>
                        <span>{label}</span>
                        <strong>{formatValue(value)}</strong>
                    </div>
                ))}
            </div>

            <div className="project-summary-details">
                <div>
                    <span>Complexity Score</span>
                    <strong>{formatValue(project.complexity_score)}</strong>
                </div>

                <div>
                    <span>Budget</span>
                    <strong>
                        {budget != null
                            ? `$${Number(budget).toLocaleString()}`
                            : "—"}
                    </strong>
                </div>

                <div>
                    <span>Current Risk</span>
                    <strong>
                        {dynamicRisk?.risk_level ||
                            project.current_risk ||
                            project.predicted_risk ||
                            "Not calculated"}
                    </strong>
                </div>
            </div>
        </section>
    );
}