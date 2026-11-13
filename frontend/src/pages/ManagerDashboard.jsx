import { useMemo, useState } from "react";

import ProjectTable from "../components/project/ProjectTable";
import ProjectFormModal from "../components/project/ProjectFormModal";
import ProjectRiskPanel from "../components/common/ProjectRiskPanel";

import { generateProjectRisk } from "../services/taskService";

const RISK_LEVELS = [
    { label: "Low", color: "#16a34a" },
    { label: "Medium", color: "#d97706" },
    { label: "High", color: "#ea580c" },
    { label: "Critical", color: "#dc2626" }
];

function getRisk(project) {
    const value =
        project?.current_risk ||
        project?.risk_level ||
        project?.predicted_risk ||
        "";

    return (
        RISK_LEVELS.find(
            item => item.label.toLowerCase() === String(value).toLowerCase()
        )?.label || "Unknown"
    );
}

export default function ManagerDashboard({
    projects = [],
    loading = false,
    error = "",
    onRefresh,
    onOpenProject
}) {
    const [showProjectModal, setShowProjectModal] = useState(false);
    const [selectedProject, setSelectedProject] = useState(null);
    const [riskLoading, setRiskLoading] = useState(false);
    const [actionError, setActionError] = useState("");
    const [actionMessage, setActionMessage] = useState("");

    const safeProjects = Array.isArray(projects) ? projects : [];

    const riskCounts = useMemo(() => {
        const counts = {
            Low: 0,
            Medium: 0,
            High: 0,
            Critical: 0
        };

        safeProjects.forEach(project => {
            const risk = getRisk(project);

            if (Object.prototype.hasOwnProperty.call(counts, risk)) {
                counts[risk] += 1;
            }
        });

        return counts;
    }, [safeProjects]);

    const totalProjects = safeProjects.length;

    const completedTasks = safeProjects.reduce(
        (total, project) => total + Number(project.completed_tasks || 0),
        0
    );

    const totalTasks = safeProjects.reduce(
        (total, project) => total + Number(project.total_tasks || 0),
        0
    );

    const overdueTasks = safeProjects.reduce(
        (total, project) => total + Number(project.overdue_tasks || 0),
        0
    );

    async function handleGenerateRisk() {
        if (!selectedProject) return;

        const id = selectedProject.id ?? selectedProject.project_id;
        if (!id) return;

        setRiskLoading(true);
        setActionError("");
        setActionMessage("");

        try {
            const result = await generateProjectRisk(id);

            if (result.success === false) {
                throw new Error(result.error || "Risk calculation failed.");
            }

            setActionMessage(
                result.message || "Risk assessment completed."
            );

            await onRefresh?.();
        } catch (err) {
            setActionError(err.message);
        } finally {
            setRiskLoading(false);
        }
    }

    function handleProjectSelection(project) {
        setSelectedProject(project);
        setActionError("");
        setActionMessage("");
    }

    function handleProjectCreated(newProjectId) {
        setShowProjectModal(false);

        onOpenProject?.({
            id: newProjectId,
            project_id: newProjectId
        });
    }

    return (
        <div className="manager-dashboard">
            <header className="manager-dashboard__header">
                <div>
                    <span className="manager-dashboard__eyebrow">
                        INFRASYNC AI
                    </span>

                    <h1>Manager Dashboard</h1>

                    <p>
                        Monitor project execution, team progress and project risk.
                    </p>
                </div>

                <button
                    type="button"
                    className="manager-dashboard__create"
                    onClick={() => setShowProjectModal(true)}
                >
                    + Create New Project
                </button>
            </header>

            {loading && (
                <div className="manager-dashboard__notice">
                    Loading projects...
                </div>
            )}

            {error && (
                <div className="manager-dashboard__error">
                    {error}
                </div>
            )}

            {actionError && (
                <div className="manager-dashboard__error">
                    {actionError}
                </div>
            )}

            {actionMessage && (
                <div className="manager-dashboard__success">
                    {actionMessage}
                </div>
            )}

            <section className="manager-dashboard__stats">
                {RISK_LEVELS.map(risk => (
                    <div
                        className="manager-dashboard__stat"
                        key={risk.label}
                    >
                        <div className="manager-dashboard__stat-heading">
                            <span>{risk.label} Risk</span>

                            <span
                                className="manager-dashboard__stat-dot"
                                style={{ background: risk.color }}
                            />
                        </div>

                        <strong style={{ color: risk.color }}>
                            {riskCounts[risk.label]}
                        </strong>

                        <span className="manager-dashboard__stat-caption">
                            {riskCounts[risk.label] === 1
                                ? "Project"
                                : "Projects"}
                        </span>
                    </div>
                ))}
            </section>

            <section className="manager-dashboard__overview">
                <div>
                    <span>Total Projects</span>
                    <strong>{totalProjects}</strong>
                </div>

                <div>
                    <span>Total Tasks</span>
                    <strong>{totalTasks}</strong>
                </div>

                <div>
                    <span>Completed Tasks</span>
                    <strong>{completedTasks}</strong>
                </div>

                <div>
                    <span>Overdue Tasks</span>
                    <strong>{overdueTasks}</strong>
                </div>
            </section>

            <main className="manager-dashboard__content">
                <section className="manager-dashboard__projects">
                    <ProjectTable
                        projects={safeProjects}
                        selectedProjectId={
                            selectedProject?.id ??
                            selectedProject?.project_id
                        }
                        onSelectProject={handleProjectSelection}
                    />

                    {!loading && safeProjects.length === 0 && (
                        <p className="manager-dashboard__empty">
                            No projects available. Create a project to get started.
                        </p>
                    )}
                </section>

                <section className="manager-dashboard__risk">
                    <ProjectRiskPanel
                        project={selectedProject}
                        role="manager"
                        loading={riskLoading}
                        onGenerateRisk={handleGenerateRisk}
                    />

                    {!selectedProject && (
                        <p className="manager-dashboard__hint">
                            Select a project from the table to view its current risk assessment.
                        </p>
                    )}
                </section>
            </main>

            <ProjectFormModal
                isOpen={showProjectModal}
                onClose={() => setShowProjectModal(false)}
                onCreated={handleProjectCreated}
            />

            <style>{`
                .manager-dashboard {
                    min-height: 100vh;
                    padding: 30px;
                    background: #f8fafc;
                    color: #0f172a;
                    box-sizing: border-box;
                }

                .manager-dashboard__header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 20px;
                    margin-bottom: 28px;
                }

                .manager-dashboard__eyebrow {
                    color: #2563eb;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                }

                .manager-dashboard__header h1 {
                    margin: 8px 0;
                    font-size: 28px;
                }

                .manager-dashboard__header p {
                    margin: 0;
                    color: #64748b;
                    font-size: 14px;
                }

                .manager-dashboard__create {
                    padding: 13px 19px;
                    background: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-weight: 600;
                    cursor: pointer;
                    white-space: nowrap;
                }

                .manager-dashboard__stats {
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 16px;
                    margin-bottom: 18px;
                }

                .manager-dashboard__stat {
                    padding: 20px;
                    border-radius: 14px;
                    background: white;
                    border: 1px solid #e2e8f0;
                }

                .manager-dashboard__stat-heading {
                    display: flex;
                    justify-content: space-between;
                    color: #64748b;
                    font-size: 13px;
                }

                .manager-dashboard__stat-dot {
                    width: 9px;
                    height: 9px;
                    border-radius: 50%;
                }

                .manager-dashboard__stat strong {
                    display: block;
                    font-size: 30px;
                    margin: 12px 0 5px;
                }

                .manager-dashboard__stat-caption {
                    color: #94a3b8;
                    font-size: 12px;
                }

                .manager-dashboard__overview {
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 16px;
                    margin-bottom: 24px;
                }

                .manager-dashboard__overview > div {
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 18px;
                }

                .manager-dashboard__overview span {
                    display: block;
                    color: #64748b;
                    font-size: 12px;
                }

                .manager-dashboard__overview strong {
                    display: block;
                    margin-top: 8px;
                    font-size: 24px;
                }

                .manager-dashboard__content {
                    display: grid;
                    grid-template-columns: minmax(0, 1fr) 320px;
                    gap: 24px;
                    align-items: start;
                }

                .manager-dashboard__projects {
                    min-width: 0;
                }

                .manager-dashboard__risk {
                    position: sticky;
                    top: 20px;
                }

                .manager-dashboard__hint,
                .manager-dashboard__empty {
                    color: #64748b;
                    font-size: 13px;
                    line-height: 1.6;
                }

                .manager-dashboard__notice,
                .manager-dashboard__error,
                .manager-dashboard__success {
                    padding: 13px 16px;
                    margin-bottom: 16px;
                    border-radius: 9px;
                    font-size: 13px;
                }

                .manager-dashboard__notice {
                    background: #eff6ff;
                    color: #1d4ed8;
                }

                .manager-dashboard__error {
                    background: #fee2e2;
                    color: #991b1b;
                }

                .manager-dashboard__success {
                    background: #dcfce7;
                    color: #166534;
                }

                @media (max-width: 900px) {
                    .manager-dashboard__content {
                        grid-template-columns: 1fr;
                    }

                    .manager-dashboard__risk {
                        position: static;
                    }
                }

                @media (max-width: 650px) {
                    .manager-dashboard {
                        padding: 18px;
                    }

                    .manager-dashboard__header {
                        align-items: stretch;
                        flex-direction: column;
                    }

                    .manager-dashboard__stats,
                    .manager-dashboard__overview {
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                    }

                    .manager-dashboard__create {
                        width: 100%;
                    }
                }
            `}</style>
        </div>
    );
}