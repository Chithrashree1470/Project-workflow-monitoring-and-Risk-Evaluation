import { useMemo, useState } from "react";
import { getProjectDetailsUrl } from "../../services/projectService";

const RISK_STYLES = {
    Low: { background: "#dcfce7", color: "#166534" },
    Medium: { background: "#fef3c7", color: "#92400e" },
    High: { background: "#ffedd5", color: "#9a3412" },
    Critical: { background: "#fee2e2", color: "#991b1b" }
};

function getRisk(project) {
    const value =
        project.current_risk ||
        project.risk_level ||
        project.predicted_risk;

    return (
        Object.keys(RISK_STYLES).find(
            (risk) =>
                risk.toLowerCase() ===
                String(value || "").toLowerCase()
        ) || "Unknown"
    );
}

function display(value) {
    return value === null || value === undefined || value === ""
        ? "—"
        : value;
}

export default function ProjectTable({
    projects = [],
    onSelectProject,
    selectedProjectId = null
}) {
    const [search, setSearch] = useState("");
    const [riskFilter, setRiskFilter] = useState("All");

    const filteredProjects = useMemo(() => {
        return projects.filter((project) => {
            const name = String(
                project.project_name ||
                project.Project_Name ||
                ""
            ).toLowerCase();

            const matchesSearch = name.includes(search.toLowerCase());

            const matchesRisk =
                riskFilter === "All" ||
                getRisk(project) === riskFilter;

            return matchesSearch && matchesRisk;
        });
    }, [projects, search, riskFilter]);

    return (
        <section className="project-table">
            <div className="project-table__toolbar">
                <div>
                    <h2>Projects</h2>
                    <p>{filteredProjects.length} projects</p>
                </div>

                <div className="project-table__filters">
                    <input
                        type="search"
                        placeholder="Search projects..."
                        value={search}
                        onChange={(event) =>
                            setSearch(event.target.value)
                        }
                    />

                    <select
                        value={riskFilter}
                        onChange={(event) =>
                            setRiskFilter(event.target.value)
                        }
                    >
                        <option value="All">All Risks</option>
                        <option value="Low">Low</option>
                        <option value="Medium">Medium</option>
                        <option value="High">High</option>
                        <option value="Critical">Critical</option>
                    </select>
                </div>
            </div>

            <div className="project-table__scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Project</th>
                            <th>Team</th>
                            <th>Budget</th>
                            <th>Timeline</th>
                            <th>Complexity</th>
                            <th>Tasks</th>
                            <th>Completed</th>
                            <th>Overdue</th>
                            <th>Risk</th>
                            <th>Details</th>
                        </tr>
                    </thead>

                    <tbody>
                        {filteredProjects.map((project) => {
                            const risk = getRisk(project);

                            return (
                                <tr
                                    key={project.id}
                                    className={
                                        String(selectedProjectId) ===
                                        String(project.id)
                                            ? "selected"
                                            : ""
                                    }
                                >
                                    <td>
                                        <button
                                            type="button"
                                            className="project-table__name"
                                            onClick={() =>
                                                onSelectProject?.(project)
                                            }
                                        >
                                            {display(
                                                project.project_name ||
                                                project.Project_Name
                                            )}
                                        </button>
                                    </td>

                                    <td>{display(project.team_size)}</td>

                                    <td>
                                        {display(
                                            project.project_budget_usd ??
                                            project.project_budget
                                        )}
                                    </td>

                                    <td>
                                        {display(
                                            project.estimated_timeline_months ??
                                            project.timeline
                                        )}
                                    </td>

                                    <td>
                                        {display(project.complexity_score)}
                                    </td>

                                    <td>{display(project.total_tasks)}</td>

                                    <td>{display(project.completed_tasks)}</td>

                                    <td>{display(project.overdue_tasks)}</td>

                                    <td>
                                        <span
                                            className="project-table__risk"
                                            style={
                                                RISK_STYLES[risk] || {
                                                    background: "#f1f5f9",
                                                    color: "#475569"
                                                }
                                            }
                                        >
                                            {risk}
                                        </span>
                                    </td>

                                    <td>
                                        <a
                                            href={getProjectDetailsUrl(project.id)}
                                            className="project-table__link"
                                        >
                                            View
                                        </a>
                                    </td>
                                </tr>
                            );
                        })}

                        {filteredProjects.length === 0 && (
                            <tr>
                                <td colSpan="10" className="project-table__empty">
                                    No matching projects found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <style>{`
                .project-table {
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 16px;
                    overflow: hidden;
                }

                .project-table__toolbar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 16px;
                    padding: 20px;
                }

                .project-table__toolbar h2 {
                    margin: 0;
                    font-size: 19px;
                    color: #0f172a;
                }

                .project-table__toolbar p {
                    margin: 5px 0 0;
                    color: #64748b;
                    font-size: 13px;
                }

                .project-table__filters {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                }

                .project-table__filters input,
                .project-table__filters select {
                    padding: 10px 12px;
                    border: 1px solid #cbd5e1;
                    border-radius: 9px;
                    background: white;
                }

                .project-table__scroll {
                    overflow-x: auto;
                }

                .project-table table {
                    width: 100%;
                    border-collapse: collapse;
                    white-space: nowrap;
                    font-size: 13px;
                }

                .project-table th {
                    background: #f8fafc;
                    color: #64748b;
                    text-align: left;
                    padding: 14px;
                    font-weight: 600;
                }

                .project-table td {
                    padding: 15px 14px;
                    border-top: 1px solid #f1f5f9;
                    color: #334155;
                }

                .project-table tr.selected {
                    background: #eff6ff;
                }

                .project-table__name {
                    border: none;
                    padding: 0;
                    background: none;
                    color: #0f172a;
                    font-weight: 600;
                    cursor: pointer;
                    text-align: left;
                }

                .project-table__risk {
                    display: inline-block;
                    border-radius: 999px;
                    padding: 5px 11px;
                    font-weight: 600;
                }

                .project-table__link {
                    color: #2563eb;
                    font-weight: 600;
                    text-decoration: none;
                }

                .project-table__empty {
                    text-align: center;
                    padding: 30px !important;
                    color: #64748b !important;
                }

                @media (max-width: 700px) {
                    .project-table__toolbar {
                        align-items: stretch;
                        flex-direction: column;
                    }
                }
            `}</style>
        </section>
    );
}