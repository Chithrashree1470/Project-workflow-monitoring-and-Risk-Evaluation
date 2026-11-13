
import { useState } from "react";
import {
    Activity, ArrowLeft, ArrowUpRight, BriefcaseBusiness,
    Building2, CheckCircle2, FolderKanban, LayoutDashboard,
    ShieldCheck, UserRound
} from "lucide-react";

import ProjectDetails from "./pages/ProjectDetails";
import ManagerDashboard from "./pages/ManagerDashboard";
import RoleProjectsDashboard from "./components/project/RoleProjectsDashboard";
import { getDashboardProjects } from "./services/projectService";
import { getRoleProjects, validateRoleId } from "./services/roleProjectsService";

import "./styles/dashboard.css";
import "./styles/role-access.css";

const roles = {
    manager: {
        title: "Manager workspace",
        subtitle: "Monitor projects, coordinate teams, and manage delivery.",
        icon: BriefcaseBusiness
    },
    employee: {
        title: "Employee workspace",
        subtitle: "View your assigned projects and tasks.",
        icon: UserRound
    },
    client: {
        title: "Client workspace",
        subtitle: "View your projects, progress, and risk information.",
        icon: Building2
    }
};

export default function App() {
    const [role, setRole] = useState("manager");
    const [identifier, setIdentifier] = useState("");
    const [projectId, setProjectId] = useState("");
    const [identity, setIdentity] = useState(null);
    const [roleProjects, setRoleProjects] = useState([]);
    const [selectedProject, setSelectedProject] = useState(null);
    const [activePage, setActivePage] = useState("home");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [managerProjects, setManagerProjects] = useState([]);
    const [managerLoading, setManagerLoading] = useState(false);
    const [managerError, setManagerError] = useState("");

    const Icon = roles[role].icon;

    async function enterRole(event) {
        event.preventDefault();
        setLoading(true);
        setError("");

        try {
            const cleanId = identifier.trim();
            const user = await validateRoleId(role, cleanId);
            const projects = await getRoleProjects(role, cleanId);

            setIdentity(user);
            setRoleProjects(projects);
            setActivePage("role-projects");
        } catch (err) {
            setError(err.message || "Unable to load your workspace.");
        } finally {
            setLoading(false);
        }
    }

    function enterManagerProject(event) {
        event.preventDefault();

        const id = projectId.trim();
        if (!id) return;

        setSelectedProject({ id });
        setActivePage("project-details");
    }

    async function openManagerDashboard() {
        setManagerLoading(true);
        setManagerError("");

        try {
            const result = await getDashboardProjects();

            if (result.success === false) {
                throw new Error(result.error || "Unable to load projects.");
            }

            setManagerProjects(result.projects || []);
            setActivePage("manager-dashboard");
        } catch (err) {
            setManagerError(err.message || "Unable to load projects.");
        } finally {
            setManagerLoading(false);
        }
    }

    async function refreshManagerDashboard() {
        setManagerLoading(true);
        setManagerError("");

        try {
            const result = await getDashboardProjects();

            if (result.success === false) {
                throw new Error(result.error || "Unable to load projects.");
            }

            setManagerProjects(result.projects || []);
        } catch (err) {
            setManagerError(err.message || "Unable to refresh projects.");
        } finally {
            setManagerLoading(false);
        }
    }

    function openProject(project) {
        setSelectedProject(project);
        setProjectId(String(project.id ?? project.project_id ?? ""));
        setActivePage("project-details");
    }

    function backToProjects() {
        if (role === "manager") {
            setActivePage("manager-dashboard");
            refreshManagerDashboard();
        } else {
            setActivePage("role-projects");
        }
    }

    function backHome() {
        setActivePage("home");
        setError("");
        setIdentifier("");
        setIdentity(null);
        setSelectedProject(null);
        setProjectId("");
    }

    return (
        <div className="app-shell">
            <header className="topbar">
                <button className="brand" onClick={backHome}>
                    <span className="brand-mark"><Activity size={21} /></span>
                    <span>InfraSync <b>AI</b></span>
                </button>
                <div className="topbar-right">
                    <span className="status-dot" />
                    Backend connection configured
                </div>
            </header>

            {activePage === "home" && (
                <main className="home-page">
                    <section className="hero">
                        <div className="eyebrow">
                            <span className="status-dot" />
                            PROJECT WORKFLOW PLATFORM
                        </div>
                        <h1>Project delivery,<br /><span>in sync.</span></h1>
                        <p className="hero-copy">
                            Choose your workspace to access the tools and
                            project information relevant to your role.
                        </p>
                        <div className="hero-stats">
                            <div><Activity size={17} /><span>Predictive risk monitoring</span></div>
                            <div><ShieldCheck size={17} /><span>Role-based project workspace</span></div>
                        </div>
                    </section>

                    <section className="portal">
                        <div className="section-heading">
                            <div>
                                <span className="eyebrow">WORKSPACE ACCESS</span>
                                <h2>Select your role</h2>
                            </div>
                            <span className="step-label">01 / 02</span>
                        </div>

                        <div className="role-grid">
                            {Object.entries(roles).map(([key, info]) => {
                                const RoleIcon = info.icon;

                                return (
                                    <button
                                        key={key}
                                        className={`role-card ${role === key ? "selected" : ""}`}
                                        onClick={() => {
                                            setRole(key);
                                            setError("");
                                            setIdentifier("");
                                        }}
                                    >
                                        <span className="role-icon"><RoleIcon size={22} /></span>
                                        <span className="role-name">
                                            {key[0].toUpperCase() + key.slice(1)}
                                        </span>
                                        <span className="role-description">{info.subtitle}</span>
                                        <span className="role-select">
                                            {role === key
                                                ? <><CheckCircle2 size={16} /> Selected</>
                                                : <>Choose view <ArrowUpRight size={15} /></>}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>

                        {role === "manager" ? (
                            <div className="project-entry">
                                <div className="project-entry-heading">
                                    <span className="entry-icon"><FolderKanban size={19} /></span>
                                    <div>
                                        <h3>Open a project</h3>
                                        <p>Enter the project ID used by your existing backend.</p>
                                    </div>
                                </div>

                                <form className="project-form" onSubmit={enterManagerProject}>
                                    <label htmlFor="project-id">Project ID</label>
                                    <div className="input-row">
                                        <input
                                            id="project-id"
                                            value={projectId}
                                            onChange={e => setProjectId(e.target.value)}
                                            placeholder="Enter project ID"
                                            required
                                        />
                                        <button type="submit" disabled={!projectId.trim()}>
                                            Continue <ArrowUpRight size={16} />
                                        </button>
                                    </div>
                                </form>

                                <button className="dashboard-link" onClick={openManagerDashboard}>
                                    <LayoutDashboard size={16} />
                                    Open manager dashboard
                                    <ArrowUpRight size={15} />
                                </button>
                            </div>
                        ) : (
                            <div className="role-access-form">
                                <form onSubmit={enterRole}>
                                    <label htmlFor="role-id">
                                        {role === "employee" ? "Employee ID" : "Client ID"}
                                    </label>
                                    <input
                                        id="role-id"
                                        value={identifier}
                                        onChange={e => setIdentifier(e.target.value)}
                                        placeholder={role === "employee"
                                            ? "Enter your EMP ID"
                                            : "Enter your Client ID"}
                                        autoComplete="off"
                                        required
                                    />
                                    <button type="submit" disabled={loading || !identifier.trim()}>
                                        {loading ? "Loading..." : "View my projects"}
                                        <ArrowUpRight size={16} />
                                    </button>
                                    {error && <p className="role-access-error">{error}</p>}
                                </form>
                            </div>
                        )}

                        <p className="note">
                            <ShieldCheck size={14} />
                            {role === "manager"
                                ? "Manager workspace"
                                : "Enter the ID registered in InfraSync to find your projects."}
                        </p>
                    </section>

                    <footer className="footer">
                        <span>INFRASYNC AI</span>
                        <span>Role-based project workspace</span>
                    </footer>
                </main>
            )}

            {activePage === "role-projects" && (
                <RoleProjectsDashboard
                    role={role}
                    identity={identity}
                    projects={roleProjects}
                    loading={false}
                    error=""
                    onSelectProject={openProject}
                    onBack={backHome}
                />
            )}

            {activePage === "manager-dashboard" && (
                <main className="workspace-page">
                    <div className="workspace-toolbar">
                        <button className="back-button" onClick={backHome}>
                            <ArrowLeft size={16} /> Back to role selection
                        </button>
                    </div>

                    <ManagerDashboard
                        projects={managerProjects}
                        loading={managerLoading}
                        error={managerError}
                        onRefresh={refreshManagerDashboard}
                        onOpenProject={openProject}
                    />
                </main>
            )}

            {activePage === "project-details" && (
                <main className="workspace-page">
                    <div className="workspace-toolbar">
                        <button className="back-button" onClick={backToProjects}>
                            <ArrowLeft size={16} />
                            Back to {role === "manager" ? "manager dashboard" : "your projects"}
                        </button>
                    </div>

                    <ProjectDetails
                        projectId={selectedProject?.id ?? selectedProject?.project_id ?? projectId}
                        role={role}
                        subjectId={
                            role === "employee"
                                ? identity?.employee_id
                                : role === "client"
                                    ? identity?.client_id
                                    : null
                        }
                    />
                </main>
            )}
        </div>
    );
}
