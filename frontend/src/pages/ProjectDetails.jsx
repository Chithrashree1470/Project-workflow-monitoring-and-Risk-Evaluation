
import { useCallback, useEffect, useState } from "react";
// import { useParams } from "react-router-dom";

import { getProjectDetails } from "../services/projectDetailsService";
import { apiRequest } from "../services/api";
import ProjectRiskPanel from "../components/common/ProjectRiskPanel";

import ProjectOverview from "../components/project/ProjectOverview";
import TeamMembersSection from "../components/project/TeamMembersSection";
import TaskSection from "../components/task/TaskSection";
import ClientsSection from "../components/project/ClientsSection";

import "../styles/project-details.css";

export default function ProjectDetails({ projectId: suppliedProjectId, role: selectedRole = "manager", subjectId: selectedSubjectId = null }) {
    const projectId =
    suppliedProjectId ||
    window.location.pathname.match(/\/project\/([^/]+)/)?.[1];

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [actionLoading, setActionLoading] = useState(false);
    const [message, setMessage] = useState("");

    const loadProject = useCallback(async () => {
        if (!projectId) {
            setError("Project ID is missing.");
            setLoading(false);
            return;
        }

        try {
            setError("");
            const result = await getProjectDetails(projectId, selectedRole, selectedSubjectId);

            if (!result.success) {
                throw new Error(result.error || "Unable to load project.");
            }

            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [projectId, selectedRole, selectedSubjectId]);

    useEffect(() => {
        loadProject();
    }, [loadProject]);

    async function handleGenerateRisk() {
        if (selectedRole !== "manager") return;
        try {
            setActionLoading(true);
            setMessage("");

            const result = await apiRequest(
                `/api/tasks/project/${projectId}/calculate-risk`,
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

    async function handleAddEmployee(employeeId) {
        if (selectedRole !== "manager") throw new Error("Only managers can manage team members.");
        const result = await apiRequest(
            `/api/project/${projectId}/employees`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ employee_id: employeeId })
            }
        );

        await loadProject();
        return result;
    }

    async function handleRemoveEmployee(employeeId) {
        if (selectedRole !== "manager") throw new Error("Only managers can manage team members.");
        const result = await apiRequest(
            `/api/project/${projectId}/employees/${employeeId}`,
            { method: "DELETE" }
        );

        await loadProject();
        return result;
    }

    async function handleUpdateTask(taskId, updates) {
        await apiRequest(`/api/tasks/${taskId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ...updates,
                updated_by: selectedSubjectId || data?.subject_id
            })
        });

        await loadProject();
    }

    async function handleDeleteTask(taskId) {
        await apiRequest(`/api/tasks/${taskId}`, {
            method: "DELETE"
        });

        await loadProject();
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
        project,
        details,
        dynamic_risk,
        task_predictions,
        role: responseRole,
        subject_id: responseSubjectId
    } = data;

    const role = selectedRole || responseRole || "manager";
    const subject_id = selectedSubjectId || responseSubjectId || null;

    return (
        <main className="project-details-page">
            <header className="project-details-header">
                <div>
                    <p className="project-eyebrow">PROJECT WORKSPACE</p>
                    <h1>{project.project_name || "Untitled Project"}</h1>
                    <span className="project-role">
                        {role} view
                    </span>
                </div>

                <button
                    className="refresh-button"
                    onClick={loadProject}
                >
                    Refresh
                </button>
            </header>

            {message && (
                <div className="project-message">{message}</div>
            )}

            <div className="project-details-layout">
                <div className="project-main-column">
                    <ProjectOverview
                        project={project}
                        dynamicRisk={dynamic_risk}
                        teamSize={details.team_members?.length || 0}
                    />

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
                        members={details.team_members || []}
                        role={role}
                        onAdd={handleAddEmployee}
                        onRemove={handleRemoveEmployee}
                    />

                    <TaskSection
                        tasks={details.tasks || []}
                        predictions={task_predictions || {}}
                        role={role}
                        subjectId={subject_id}
                        onUpdate={handleUpdateTask}
                        onDelete={handleDeleteTask}
                    />

                    <ClientsSection
                        clients={details.clients || []}
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
                        <strong>{project.id}</strong>

                        <span>Project Type</span>
                        <strong>
                            {project.project_type || project.type || "Not specified"}
                        </strong>

                        <span>Current Role</span>
                        <strong>{role}</strong>
                    </div>
                </aside>
            </div>
        </main>
    );
}
