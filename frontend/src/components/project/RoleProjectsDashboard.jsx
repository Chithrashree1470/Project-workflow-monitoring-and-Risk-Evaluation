import { useState } from "react";

export default function RoleProjectsDashboard({ role, identity, projects = [], loading, error, onSelectProject, onBack }) {
    const [query, setQuery] = useState("");
    const title = role === "employee"
        ? identity?.employee_name || identity?.name || identity?.employee_id
        : identity?.client_name || identity?.name || identity?.client_id;
    const filtered = projects.filter((project) =>
        `${project.project_name || project.name || ""} ${project.id || project.project_id || ""}`
            .toLowerCase().includes(query.toLowerCase())
    );

    return (
        <main className="role-projects-page">
            <div className="role-projects-toolbar">
                <button className="back-button" onClick={onBack}>← Back to role selection</button>
                <span className="role-projects-badge">{role} workspace</span>
            </div>
            <header className="role-projects-heading">
                <p className="project-eyebrow">YOUR WORKSPACE</p>
                <h1>Welcome, {title || "User"}</h1>
                <p>Projects associated with {role === "employee" ? "your employee ID" : "your client ID"}.</p>
            </header>
            <div className="role-projects-list-header">
                <h2>Your Projects ({filtered.length})</h2>
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search projects..." aria-label="Search projects" />
            </div>
            {loading && <p>Loading your projects...</p>}
            {error && <p className="role-projects-error">{error}</p>}
            {!loading && !error && filtered.length === 0 && <p className="role-projects-empty">No projects are associated with this ID.</p>}
            <div className="role-projects-grid">
                {filtered.map((project) => {
                    const id = project.id ?? project.project_id;
                    return (
                        <button className="role-project-card" key={id} onClick={() => onSelectProject(project)}>
                            <span className="project-eyebrow">PROJECT ID: {id}</span>
                            <strong>{project.project_name || project.name || "Untitled Project"}</strong>
                            <span>{project.project_type || project.type || "Project"}</span>
                            <span className="role-project-open">Open project details →</span>
                        </button>
                    );
                })}
            </div>
        </main>
    );
}
