
import { useCallback, useEffect, useState } from "react";

import { getProjectDetails } from "../services/projectDetailsService";
import { apiRequest } from "../services/api";
import { createTask } from "../services/taskService";

import ProjectRiskPanel from "../components/common/ProjectRiskPanel";
import ProjectOverview from "../components/project/ProjectOverview";
import TeamMembersSection from "../components/project/TeamMembersSection";
import TaskSection from "../components/task/TaskSection";
import ClientsSection from "../components/project/ClientsSection";

import "../styles/project-details.css";

function dateValue(value) {
    return value ? String(value).slice(0, 10) : "";
}

function getBudget(project, details) {
    return (
        project?.project_budget ??
        project?.project_budget_usd ??
        details?.project_budget ??
        details?.Project_Budget_USD ??
        null
    );
}

export default function ProjectDetails({
    projectId: suppliedProjectId,
    role: selectedRole = "manager",
    subjectId: selectedSubjectId = null
}) {
    const projectId = suppliedProjectId;

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [actionLoading, setActionLoading] = useState(false);
    const [message, setMessage] = useState("");

    const [editingDates, setEditingDates] = useState(false);
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [savingDates, setSavingDates] = useState(false);

    const isManager = selectedRole === "manager";

    const loadProject = useCallback(async () => {
        if (!projectId) {
            setError("Project ID is missing.");
            setLoading(false);
            return;
        }

        try {
            setError("");

            const result = await getProjectDetails(
                projectId,
                selectedRole,
                selectedSubjectId
            );

            if (!result.success) {
                throw new Error(result.error || "Unable to load project.");
            }

            setData(result);

            const project = result.project || {};
            const details = result.details || {};

            setStartDate(dateValue(
                details.start_date ||
                project.start_date ||
                project.project_details?.start_date
            ));

            setEndDate(dateValue(
                details.end_date ||
                project.end_date ||
                project.project_details?.end_date
            ));
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [projectId, selectedRole, selectedSubjectId]);

    useEffect(() => {
        loadProject();
    }, [loadProject]);

    // Risk generation is intentionally left unchanged for now.
    async function handleGenerateRisk() {
        if (!isManager) return;

        try {
            setActionLoading(true);
            setMessage("");

            const result = await apiRequest(
                `/api/tasks/project/${encodeURIComponent(projectId)}/calculate-risk`,
                { method: "POST" }
            );

            setMessage(result.message || "Risk calculated successfully.");
            await loadProject();
        } catch (err) {
            setMessage(err.message);
        } finally {
            setActionLoading(false);
        }
    }

    async function handleSaveDates() {
        if (!isManager) return;

        if (startDate && endDate && endDate < startDate) {
            setMessage("Project end date cannot be before its start date.");
            return;
        }

        try {
            setSavingDates(true);
            setMessage("");

            const result = await apiRequest(
                `/api/project/${encodeURIComponent(projectId)}/details`,
                {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        start_date: startDate,
                        end_date: endDate
                    })
                }
            );

            if (result.success === false) {
                throw new Error(
                    result.error || result.message || "Project update failed."
                );
            }

            setEditingDates(false);
            setMessage("Project dates updated.");
            await loadProject();
        } catch (err) {
            setMessage(err.message);
        } finally {
            setSavingDates(false);
        }
    }

    async function handleAddEmployee(employeeId) {
        if (!isManager) {
            throw new Error("Only managers can manage team members.");
        }

        const result = await apiRequest(
            `/api/project/${encodeURIComponent(projectId)}/employees`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ employee_id: employeeId })
            }
        );

        if (result.success === false) {
            throw new Error(result.error || result.message || "Unable to add employee.");
        }

        await loadProject();
        return result;
    }

    async function handleRemoveEmployee(employeeId) {
        if (!isManager) {
            throw new Error("Only managers can manage team members.");
        }

        const result = await apiRequest(
            `/api/project/${encodeURIComponent(projectId)}/employees/${encodeURIComponent(employeeId)}`,
            { method: "DELETE" }
        );

        if (result.success === false) {
            throw new Error(result.error || result.message || "Unable to remove employee.");
        }

        await loadProject();
        return result;
    }

    async function handleAddClient(clientId) {
        if (!isManager) {
            throw new Error("Only managers can manage clients.");
        }

        const result = await apiRequest(
            `/api/project/${encodeURIComponent(projectId)}/clients`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id: clientId })
            }
        );

        if (result.success === false) {
            throw new Error(result.error || result.message || "Unable to add client.");
        }

        await loadProject();
        return result;
    }

    async function handleRemoveClient(clientId) {
        if (!isManager) {
            throw new Error("Only managers can manage clients.");
        }

        const result = await apiRequest(
            `/api/project/${encodeURIComponent(projectId)}/clients/${encodeURIComponent(clientId)}`,
            { method: "DELETE" }
        );

        if (result.success === false) {
            throw new Error(result.error || result.message || "Unable to remove client.");
        }

        await loadProject();
        return result;
    }

    async function handleCreateTask(taskData) {
        if (!isManager) {
            throw new Error("Only managers can create tasks.");
        }

        const result = await createTask({
            ...taskData,
            project_id: projectId
        });

        if (result.success === false) {
            throw new Error(result.error || result.message || "Unable to create task.");
        }

        await loadProject();
        return result;
    }

    async function handleUpdateTask(taskId, updates) {
        const result = await apiRequest(
            `/api/tasks/${encodeURIComponent(taskId)}`,
            {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...updates,
                    updated_by: selectedSubjectId || data?.subject_id
                })
            }
        );

        if (result.success === false) {
            throw new Error(result.error || result.message || "Unable to update task.");
        }

        await loadProject();
        return result;
    }

    async function handleDeleteTask(taskId) {
        const result = await apiRequest(
            `/api/tasks/${encodeURIComponent(taskId)}`,
            { method: "DELETE" }
        );

        if (result.success === false) {
            throw new Error(result.error || result.message || "Unable to delete task.");
        }

        await loadProject();
        return result;
    }

    if (loading) {
        return <div className="project-loading">Loading project details...</div>;
    }

    if (error) {
        return (
            <div className="project-error">
                <p>{error}</p>
                <button onClick={loadProject}>Retry</button>
            </div>
        );
    }

    if (!data) return null;

    const {
        project = {},
        details = {},
        dynamic_risk,
        task_predictions,
        role: responseRole,
        subject_id: responseSubjectId
    } = data;

    const role = selectedRole || responseRole || "manager";
    const subjectId = selectedSubjectId || responseSubjectId || null;

    const budget = getBudget(project, details);
    const formattedBudget = budget == null
        ? "Not specified"
        : `$${Number(budget).toLocaleString()}`;

    const teamMembers = details.team_members || [];
    const tasks = details.tasks || [];
    const clients = details.clients || [];

    return (
        <main className="project-details-page">
            <header className="project-details-header">
                <div>
                    <p className="project-eyebrow">PROJECT WORKSPACE</p>
                    <h1>{project.project_name || "Untitled Project"}</h1>
                    <span className="project-role">{role} view</span>
                </div>

                <button className="refresh-button" onClick={loadProject}>
                    Refresh
                </button>
            </header>

            {message && <div className="project-message">{message}</div>}

            <div className="project-details-layout">
                <div className="project-main-column">
                    <ProjectOverview
                        project={{
                            ...project,
                            project_budget_usd: budget
                        }}
                        details={details}
                        dynamicRisk={dynamic_risk}
                        teamSize={teamMembers.length}
                    />

                    <section className="project-section">
                        <div className="project-section-heading">
                            <h2>Project Timeline</h2>

                            {isManager && !editingDates && (
                                <button
                                    type="button"
                                    className="primary-button"
                                    onClick={() => setEditingDates(true)}
                                >
                                    Edit Dates
                                </button>
                            )}
                        </div>

                        {editingDates ? (
                            <div className="project-date-editor">
                                <label>
                                    Start Date
                                    <input
                                        type="date"
                                        value={startDate}
                                        onChange={event => setStartDate(event.target.value)}
                                    />
                                </label>

                                <label>
                                    End Date
                                    <input
                                        type="date"
                                        min={startDate || undefined}
                                        value={endDate}
                                        onChange={event => setEndDate(event.target.value)}
                                    />
                                </label>

                                <div className="project-date-actions">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setEditingDates(false);
                                            loadProject();
                                        }}
                                        disabled={savingDates}
                                    >
                                        Cancel
                                    </button>

                                    <button
                                        type="button"
                                        className="primary-button"
                                        onClick={handleSaveDates}
                                        disabled={savingDates}
                                    >
                                        {savingDates ? "Saving..." : "Save Dates"}
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="project-date-display">
                                <div>
                                    <span>Start Date</span>
                                    <strong>{startDate || "Not specified"}</strong>
                                </div>

                                <div>
                                    <span>End Date</span>
                                    <strong>{endDate || "Not specified"}</strong>
                                </div>
                            </div>
                        )}
                    </section>

                    <section className="project-section">
                        <h2>Project Skill Requirements</h2>

                        <div className="technology-list">
                            {(project.required_technologies || []).map(
                                (technology, index) => (
                                    <span key={`${technology}-${index}`}>
                                        {technology}
                                    </span>
                                )
                            )}

                            {(!project.required_technologies ||
                                project.required_technologies.length === 0) && (
                                <p>No required technologies recorded.</p>
                            )}
                        </div>

                        <div className="skill-metrics">
                            <div>
                                <span>Skill Coverage</span>
                                <strong>
                                    {Number(project.skill_coverage || 0).toFixed(2)}%
                                </strong>
                            </div>

                            <div>
                                <span>Skill Gap</span>
                                <strong>
                                    {Number(project.skill_gap || 0).toFixed(2)}%
                                </strong>
                            </div>
                        </div>
                    </section>

                    <TeamMembersSection
                        members={teamMembers}
                        role={role}
                        onAdd={handleAddEmployee}
                        onRemove={handleRemoveEmployee}
                    />

                    <TaskSection
                        tasks={tasks}
                        predictions={task_predictions || {}}
                        role={role}
                        subjectId={subjectId}
                        onCreate={handleCreateTask}
                        onUpdate={handleUpdateTask}
                        onDelete={handleDeleteTask}
                    />

                    <ClientsSection
                        clients={clients}
                        role={role}
                        onAdd={handleAddClient}
                        onRemove={handleRemoveClient}
                    />
                </div>

                <aside className="project-sidebar">
                    <ProjectRiskPanel
                        project={project}
                        role={role}
                        loading={actionLoading}
                        onGenerateRisk={handleGenerateRisk}
                    />

                    <div className="project-sidebar-info">
                        <span>Project ID</span>
                        <strong>{project.id ?? project.project_id ?? projectId}</strong>

                        <span>Project Type</span>
                        <strong>
                            {project.project_type || project.type || "Not specified"}
                        </strong>

                        <span>Current Role</span>
                        <strong>{role}</strong>
                    </div>
                </aside>
            </div>

            <style>{`
                .project-section-heading {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 12px;
                }

                .project-section-heading h2 {
                    margin: 0;
                }

                .project-date-editor,
                .project-date-display {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 18px;
                    margin-top: 18px;
                }

                .project-date-editor label {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    color: #cbd5e1;
                    font-size: 13px;
                }

                .project-date-editor input {
                    padding: 11px;
                    border: 1px solid #475569;
                    border-radius: 8px;
                    color: #f8fafc;
                    background: #0b1728;
                }

                .project-date-actions {
                    grid-column: 1 / -1;
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                }

                .project-date-actions button {
                    padding: 10px 15px;
                    border: 1px solid #475569;
                    border-radius: 8px;
                    background: #17263a;
                    color: #e2e8f0;
                    cursor: pointer;
                }

                @media (max-width: 550px) {
                    .project-date-editor,
                    .project-date-display {
                        grid-template-columns: 1fr;
                    }
                }
            `}</style>
        </main>
    );
}
