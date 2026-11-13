import { useCallback, useEffect, useState } from "react";

import {
    getProjectDetails,
    updateProjectDetails,
    addProjectClient,
    removeProjectClient
} from "../services/projectDetailsService";

import { apiRequest } from "../services/api";

import {
    createTask,
    updateTask,
    deleteTask
} from "../services/taskService";

import ProjectRiskPanel from "../components/common/ProjectRiskPanel";
import ProjectOverview from "../components/project/ProjectOverview";
import TeamMembersSection from "../components/project/TeamMembersSection";
import TaskSection from "../components/task/TaskSection";
import ClientsSection from "../components/project/ClientsSection";
import ProjectFormModal from "../components/project/ProjectFormModal";

import "../styles/project-details.css";

const DEFAULT_TECHNOLOGIES = [
    "Python",
    "Java",
    "JavaScript",
    "React",
    "Node.js",
    "Flask",
    "Spring Boot",
    "SQL",
    "PostgreSQL",
    "MongoDB",
    "REST API",
    "Docker",
    "AWS",
    "Machine Learning"
];

function toTechnologyArray(value) {
    if (Array.isArray(value)) return value;

    if (!value) return [];

    if (typeof value === "string") {
        try {
            const parsed = JSON.parse(value);

            if (Array.isArray(parsed)) return parsed;
        } catch {
            return value
                .split(",")
                .map(item => item.trim())
                .filter(Boolean);
        }
    }

    return [];
}

function dateValue(value) {
    return value ? String(value).slice(0, 10) : "";
}

function getProgressStatus(project, details) {
    const status =
        project.project_progress ||
        details.project_progress ||
        project.progress_status;

    // The backend may store progress as a text status.
    if (typeof status === "string" && status.trim()) {
        return status;
    }

    const completion = Number(
        project.completion_percentage ??
        details.completion_percentage ??
        0
    );

    if (completion >= 100) return "Completed";
    if (completion > 0) return "In Progress";

    return "Not Started";
}

function getProjectBudget(project, details) {
    return (
        project.project_budget ??
        project.project_budget_usd ??
        details.project_budget ??
        details.project_budget_usd ??
        null
    );
}

export default function ProjectDetails({
    projectId: suppliedProjectId,
    role: selectedRole = "manager",
    subjectId: selectedSubjectId = null,
    onOpenProject
}) {
    const projectId = suppliedProjectId;

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [actionLoading, setActionLoading] = useState(false);
    const [message, setMessage] = useState("");

    const [showCreateProject, setShowCreateProject] = useState(false);
    const [editingProject, setEditingProject] = useState(false);

    const [requiredTechnologies, setRequiredTechnologies] = useState([]);
    const [customTechnology, setCustomTechnology] = useState("");

    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");

    const isManager = String(selectedRole).toLowerCase() === "manager";

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
                throw new Error(
                    result.error || "Unable to load project."
                );
            }

            setData(result);

            const project = result.project || {};
            const details = result.details || {};
            const projectDetails = project.project_details || {};

            setRequiredTechnologies(
                toTechnologyArray(project.required_technologies)
            );

            setStartDate(dateValue(
                details.start_date ||
                projectDetails.start_date ||
                project.start_date
            ));

            setEndDate(dateValue(
                details.end_date ||
                projectDetails.end_date ||
                project.end_date
            ));

        } catch (err) {
            setError(err.message || "Unable to load project.");
        } finally {
            setLoading(false);
        }
    }, [projectId, selectedRole, selectedSubjectId]);

    useEffect(() => {
        loadProject();
    }, [loadProject]);

    async function handleGenerateRisk() {
        if (!isManager) return;

        try {
            setActionLoading(true);
            setMessage("");

            const result = await apiRequest(
                `/api/tasks/project/${encodeURIComponent(projectId)}/calculate-risk`,
                {
                    method: "POST"
                }
            );

            setMessage(
                result.message || "Risk calculated successfully."
            );

            await loadProject();

        } catch (err) {
            setMessage(err.message);
        } finally {
            setActionLoading(false);
        }
    }

    async function handleSaveProject() {
        if (!isManager) return;

        if (
            startDate &&
            endDate &&
            endDate < startDate
        ) {
            setMessage(
                "Project deadline cannot be before its start date."
            );
            return;
        }

        try {
            setActionLoading(true);
            setMessage("");

            const result = await updateProjectDetails(projectId, {
                required_technologies: requiredTechnologies,
                start_date: startDate,
                end_date: endDate
            });

            if (result.success === false) {
                throw new Error(
                    result.error ||
                    result.message ||
                    "Project update failed."
                );
            }

            setEditingProject(false);
            setMessage("Project details updated successfully.");

            await loadProject();

        } catch (err) {
            setMessage(err.message);
        } finally {
            setActionLoading(false);
        }
    }

    function toggleTechnology(technology) {
        setRequiredTechnologies(previous =>
            previous.includes(technology)
                ? previous.filter(item => item !== technology)
                : [...previous, technology]
        );
    }

    function addCustomTechnology() {
        const value = customTechnology.trim();

        if (!value) return;

        setRequiredTechnologies(previous =>
            previous.some(
                item => item.toLowerCase() === value.toLowerCase()
            )
                ? previous
                : [...previous, value]
        );

        setCustomTechnology("");
    }

    async function handleAddEmployee(employeeId) {
        if (!isManager) {
            throw new Error("Only managers can manage team members.");
        }

        const result = await apiRequest(
            `/api/project/${projectId}/employees`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    employee_id: employeeId
                })
            }
        );

        await loadProject();

        return result;
    }

    async function handleRemoveEmployee(employeeId) {
        if (!isManager) {
            throw new Error("Only managers can manage team members.");
        }

        const result = await apiRequest(
            `/api/project/${projectId}/employees/${encodeURIComponent(employeeId)}`,
            {
                method: "DELETE"
            }
        );

        await loadProject();

        return result;
    }

    async function handleAddClient(clientId) {
        if (!isManager) {
            throw new Error("Only managers can add clients.");
        }

        const result = await addProjectClient(projectId, clientId);

        await loadProject();

        return result;
    }

    async function handleRemoveClient(clientId) {
        if (!isManager) {
            throw new Error("Only managers can remove clients.");
        }

        const result = await removeProjectClient(projectId, clientId);

        await loadProject();

        return result;
    }

    async function handleCreateTask(taskData) {
        if (!isManager) {
            throw new Error("Only managers can create tasks.");
        }

        await createTask({
            ...taskData,
            project_id: projectId,
            created_by: "Manager",

            // New tasks always start with zero actual hours.
            actual_hours: 0
        });

        await loadProject();
    }

    async function handleUpdateTask(taskId, updates) {
        if (!isManager && selectedRole !== "employee") {
            throw new Error("You cannot update this task.");
        }

        await updateTask(taskId, {
            ...updates,
            updated_by: selectedSubjectId || data?.subject_id || "Manager"
        });

        await loadProject();
    }

    async function handleDeleteTask(taskId) {
        if (!isManager) {
            throw new Error("Only managers can delete tasks.");
        }

        await deleteTask(taskId);

        await loadProject();
    }

    function handleProjectCreated(newProjectId) {
        setShowCreateProject(false);

        // Use the parent React navigation handler when available.
        onOpenProject?.({ id: newProjectId });
    }

    if (loading) {
        return (
            <div className="project-loading">
                Loading project details...
            </div>
        );
    }

    if (error) {
        return (
            <div className="project-error">
                <p>{error}</p>

                <button onClick={loadProject}>
                    Retry
                </button>
            </div>
        );
    }

    if (!data) return null;

    const {
        project = {},
        details = {},
        dynamic_risk,
        task_predictions
    } = data;

    const budget = getProjectBudget(project, details);
    const progressStatus = getProgressStatus(project, details);

    const completionPercentage = Number(
        project.completion_percentage ??
        details.completion_percentage ??
        0
    );

    // Normalize the values expected by the existing ProjectOverview component.
    const overviewProject = {
        ...project,
        project_budget_usd: budget,
        project_progress: completionPercentage
    };

    return (
        <main className="project-details-page">

            <header className="project-details-header">
                <div>
                    <p className="project-eyebrow">
                        PROJECT WORKSPACE
                    </p>

                    <h1>
                        {project.project_name || "Untitled Project"}
                    </h1>

                    <span className="project-role">
                        {selectedRole} view
                    </span>
                </div>

                <div className="project-header-actions">
                    {isManager && (
                        <button
                            className="project-action-button"
                            onClick={() => setShowCreateProject(true)}
                        >
                            + Create New Project
                        </button>
                    )}

                    <button
                        className="refresh-button"
                        onClick={loadProject}
                    >
                        Refresh
                    </button>
                </div>
            </header>

            {message && (
                <div className="project-message" role="status">
                    {message}
                </div>
            )}

            <div className="project-details-layout">

                <div className="project-main-column">

                    <ProjectOverview
                        project={overviewProject}
                        details={details}
                        dynamicRisk={dynamic_risk}
                        teamSize={details.team_members?.length || 0}
                    />

                    {/* Explicit project status and budget display */}
                    <section className="project-section project-summary-section">
                        <h2>Project Progress & Budget</h2>

                        <div className="project-summary-grid">
                            <div className="project-summary-card">
                                <span>Progress Status</span>
                                <strong>{progressStatus}</strong>
                            </div>

                            <div className="project-summary-card">
                                <span>Project Budget</span>
                                <strong>
                                    {budget !== null && budget !== undefined
                                        ? `$${Number(budget).toLocaleString()}`
                                        : "Not specified"}
                                </strong>
                            </div>

                            <div className="project-summary-card">
                                <span>Completion</span>
                                <strong>
                                    {completionPercentage.toFixed(1)}%
                                </strong>
                            </div>
                        </div>
                    </section>

                    {/* Project technologies and timeline */}
                    <section className="project-section">

                        <div className="section-heading-row">
                            <h2>Project Details</h2>

                            {isManager && (
                                <button
                                    className="project-action-button"
                                    onClick={() => {
                                        setEditingProject(value => !value);
                                        setMessage("");
                                    }}
                                >
                                    {editingProject
                                        ? "Cancel Edit"
                                        : "Edit Project"}
                                </button>
                            )}
                        </div>

                        {editingProject ? (
                            <div className="project-edit-form">

                                <h3>Required Technologies</h3>

                                <div className="technology-checkboxes">
                                    {[...new Set([
                                        ...DEFAULT_TECHNOLOGIES,
                                        ...requiredTechnologies
                                    ])].map(technology => (
                                        <label key={technology}>
                                            <input
                                                type="checkbox"
                                                checked={requiredTechnologies.includes(
                                                    technology
                                                )}
                                                onChange={() =>
                                                    toggleTechnology(technology)
                                                }
                                            />

                                            <span>{technology}</span>
                                        </label>
                                    ))}
                                </div>

                                <div className="technology-add-row">
                                    <input
                                        value={customTechnology}
                                        onChange={event =>
                                            setCustomTechnology(event.target.value)
                                        }
                                        onKeyDown={event => {
                                            if (event.key === "Enter") {
                                                event.preventDefault();
                                                addCustomTechnology();
                                            }
                                        }}
                                        placeholder="Add another technology"
                                    />

                                    <button
                                        type="button"
                                        onClick={addCustomTechnology}
                                    >
                                        Add
                                    </button>
                                </div>

                                <h3>Project Timeline</h3>

                                <div className="project-date-fields">
                                    <label>
                                        Start Date

                                        <input
                                            type="date"
                                            value={startDate}
                                            onChange={event =>
                                                setStartDate(event.target.value)
                                            }
                                            required
                                        />
                                    </label>

                                    <label>
                                        Project Deadline

                                        <input
                                            type="date"
                                            value={endDate}
                                            onChange={event =>
                                                setEndDate(event.target.value)
                                            }
                                            required
                                        />
                                    </label>
                                </div>

                                <button
                                    className="project-action-button"
                                    disabled={actionLoading}
                                    onClick={handleSaveProject}
                                >
                                    {actionLoading
                                        ? "Saving..."
                                        : "Save Project Changes"}
                                </button>
                            </div>
                        ) : (
                            <>
                                <div className="technology-list">
                                    {toTechnologyArray(
                                        project.required_technologies
                                    ).map((technology, index) => (
                                        <span key={`${technology}-${index}`}>
                                            {technology}
                                        </span>
                                    ))}

                                    {toTechnologyArray(
                                        project.required_technologies
                                    ).length === 0 && (
                                        <p>
                                            No required technologies recorded.
                                        </p>
                                    )}
                                </div>

                                <div className="project-date-display">
                                    <div>
                                        <span>Start Date</span>
                                        <strong>
                                            {startDate || "Not specified"}
                                        </strong>
                                    </div>

                                    <div>
                                        <span>Project Deadline</span>
                                        <strong>
                                            {endDate || "Not specified"}
                                        </strong>
                                    </div>
                                </div>

                                <div className="skill-metrics">
                                    <div>
                                        <span>Skill Coverage</span>

                                        <strong>
                                            {Number(
                                                project.skill_coverage || 0
                                            ).toFixed(2)}%
                                        </strong>
                                    </div>

                                    <div>
                                        <span>Skill Gap</span>

                                        <strong>
                                            {Number(
                                                project.skill_gap || 0
                                            ).toFixed(2)}%
                                        </strong>
                                    </div>
                                </div>
                            </>
                        )}
                    </section>

                    <TeamMembersSection
                        members={details.team_members || []}
                        role={selectedRole}
                        onAdd={handleAddEmployee}
                        onRemove={handleRemoveEmployee}
                    />

                    <TaskSection
                        tasks={details.tasks || []}
                        predictions={task_predictions || {}}
                        role={selectedRole}
                        subjectId={data.subject_id}
                        onCreate={handleCreateTask}
                        onUpdate={handleUpdateTask}
                        onDelete={handleDeleteTask}
                    />

                    <ClientsSection
                        clients={details.clients || []}
                        role={selectedRole}
                        onAdd={handleAddClient}
                        onRemove={handleRemoveClient}
                    />

                </div>

                <aside className="project-sidebar">

                    <ProjectRiskPanel
                        project={{
                            ...project,
                            dynamic_risk_score: dynamic_risk?.risk_score,
                            risk_trend: dynamic_risk?.risk_trend,
                            risk_level: dynamic_risk?.risk_level
                        }}
                        role={selectedRole}
                        loading={actionLoading}
                        onGenerateRisk={handleGenerateRisk}
                    />

                    <div className="project-sidebar-info">
                        <span>Project ID</span>
                        <strong>{project.id}</strong>

                        <span>Project Type</span>
                        <strong>
                            {project.project_type ||
                                project.type ||
                                "Not specified"}
                        </strong>

                        <span>Current Role</span>
                        <strong>{selectedRole}</strong>
                    </div>

                </aside>
            </div>

            {isManager && (
                <ProjectFormModal
                    isOpen={showCreateProject}
                    onClose={() => setShowCreateProject(false)}
                    onCreated={handleProjectCreated}
                />
            )}

            <style>{`
                .project-header-actions,
                .section-heading-row {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                }

                .project-action-button {
                    border: 0;
                    border-radius: 8px;
                    padding: 10px 14px;
                    background: #2563eb;
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                }

                .project-action-button:disabled {
                    opacity: .6;
                    cursor: wait;
                }

                .project-edit-form {
                    padding: 18px;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                }

                .project-edit-form h3 {
                    color: #0f172a;
                    font-size: 14px;
                    margin: 16px 0 10px;
                }

                .technology-checkboxes {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    margin: 14px 0;
                }

                .technology-checkboxes label {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 13px;
                    color: #334155;
                    cursor: pointer;
                }

                .technology-checkboxes input {
                    accent-color: #2563eb;
                }

                .technology-add-row,
                .project-date-fields {
                    display: flex;
                    gap: 12px;
                    margin: 14px 0;
                }

                .technology-add-row input,
                .project-date-fields input {
                    padding: 10px;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    color: #0f172a;
                    background: #fff;
                }

                .technology-add-row input {
                    flex: 1;
                }

                .technology-add-row button {
                    border: 0;
                    border-radius: 8px;
                    padding: 9px 16px;
                    background: #eff6ff;
                    color: #1d4ed8;
                    cursor: pointer;
                }

                .project-date-fields label {
                    display: flex;
                    flex-direction: column;
                    gap: 7px;
                    flex: 1;
                    font-size: 13px;
                    color: #475569;
                }

                .project-date-fields input {
                    width: 100%;
                    box-sizing: border-box;
                }

                .project-message {
                    padding: 12px;
                    margin: 12px 0;
                    background: #eff6ff;
                    color: #1d4ed8;
                    border-radius: 8px;
                }

                .project-summary-grid {
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 14px;
                }

                .project-summary-card {
                    display: flex;
                    flex-direction: column;
                    gap: 9px;
                    padding: 16px;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                    background: #ffffff;
                    min-width: 0;
                }

                .project-summary-card span,
                .project-date-display span {
                    color: #64748b;
                    font-size: 12px;
                }

                .project-summary-card strong {
                    color: #0f172a;
                    font-size: 17px;
                    overflow-wrap: anywhere;
                }

                .project-date-display {
                    display: flex;
                    gap: 28px;
                    margin: 18px 0;
                }

                .project-date-display > div {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .project-date-display strong {
                    color: #0f172a;
                    font-size: 14px;
                }

                @media(max-width: 700px) {
                    .project-date-fields,
                    .technology-add-row {
                        flex-direction: column;
                    }

                    .project-header-actions {
                        align-items: flex-start;
                        flex-direction: column;
                    }

                    .project-summary-grid {
                        grid-template-columns: 1fr;
                    }
                }
            `}</style>
        </main>
    );
}