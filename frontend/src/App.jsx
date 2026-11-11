import { useCallback, useEffect, useState } from "react";
import {
    Activity,
    ArrowLeft,
    ArrowUpRight,
    BriefcaseBusiness,
    CheckCircle2,
    ExternalLink,
    FolderKanban,
    LayoutDashboard,
    ShieldCheck,
    UserRound,
    Building2
} from "lucide-react";
import ProjectDetails from "./pages/ProjectDetails";
import ManagerDashboard from "./pages/ManagerDashboard";
import { getDashboardProjects } from "./services/projectService";

import "./styles/dashboard.css";

const FLASK_BASE = import.meta.env.VITE_FLASK_BASE_URL || "";

const roleInfo = {
    manager: {
        title: "Manager workspace",
        subtitle: "Monitor projects, coordinate teams, and manage delivery.",
        icon: BriefcaseBusiness,
        projectView: "manager"
    },
    employee: {
        title: "Employee workspace",
        subtitle: "Review your assigned work and follow project progress.",
        icon: UserRound,
        projectView: "employee"
    },
    client: {
        title: "Client workspace",
        subtitle: "View project progress, tasks, and risk information.",
        icon: Building2,
        projectView: "client"
    }
};

function App() {
    const [role, setRole] = useState("manager");
    const [projectId, setProjectId] = useState("");

    const [activePage, setActivePage] = useState("home");
    const [activeUrl, setActiveUrl] = useState("");

    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const selected = roleInfo[role];

    // Load projects for the React manager dashboard.
    const loadProjects = useCallback(async () => {
        try {
            setLoading(true);
            setError("");

            const data = await getDashboardProjects();

            if (!data.success) {
                throw new Error(data.error || "Unable to load projects.");
            }

            setProjects(data.projects || []);
        } catch (err) {
            setError(err.message || "Unable to connect to the backend.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (activePage === "manager-dashboard") {
            loadProjects();
        }
    }, [activePage, loadProjects]);

    // Open the existing Flask project-details page.
    function openProject(event) {
        event.preventDefault();

        const id = projectId.trim();

        if (!id) return;

        const url = `/project/${encodeURIComponent(id)}?view=${selected.projectView}`;

        setActiveUrl(url);
        setActivePage("flask-project");
    }

    // Open the React manager dashboard.
    function openDashboard() {
        setActivePage("manager-dashboard");
    }

    function goHome() {
        setActivePage("home");
        setActiveUrl("");
        setError("");
    }

    const RoleIcon = selected.icon;

    return (
        <div className="app-shell">

            <header className="topbar">
                <button
                    className="brand"
                    onClick={goHome}
                    aria-label="InfraSync home"
                >
                    <span className="brand-mark">
                        <Activity size={21} />
                    </span>
                    <span>
                        InfraSync <b>AI</b>
                    </span>
                </button>

                <div className="topbar-right">
                    <span className="status-dot" />
                    Backend connection configured
                </div>
            </header>

            {/* HOME / ROLE SELECTION */}
            {activePage === "home" && (
                <main className="home-page">

                    <section className="hero">
                        <div className="eyebrow">
                            <span className="status-dot" />
                            PROJECT WORKFLOW PLATFORM
                        </div>

                        <h1>
                            Project delivery,
                            <br />
                            <span>in sync.</span>
                        </h1>

                        <p className="hero-copy">
                            Choose your workspace to access the tools and
                            project information relevant to your role.
                        </p>

                        <div className="hero-stats">
                            <div>
                                <Activity size={17} />
                                <span>Predictive risk monitoring</span>
                            </div>

                            <div>
                                <ShieldCheck size={17} />
                                <span>Existing backend preserved</span>
                            </div>
                        </div>
                    </section>

                    <section className="portal">

                        <div className="section-heading">
                            <div>
                                <span className="eyebrow">
                                    WORKSPACE ACCESS
                                </span>
                                <h2>Select your role</h2>
                            </div>

                            <span className="step-label">01 / 02</span>
                        </div>

                        <div className="role-grid">
                            {Object.entries(roleInfo).map(([key, info]) => {
                                const Icon = info.icon;

                                return (
                                    <button
                                        key={key}
                                        className={`role-card ${
                                            role === key ? "selected" : ""
                                        }`}
                                        onClick={() => setRole(key)}
                                    >
                                        <span className="role-icon">
                                            <Icon size={22} />
                                        </span>

                                        <span className="role-name">
                                            {key[0].toUpperCase() + key.slice(1)}
                                        </span>

                                        <span className="role-description">
                                            {info.subtitle}
                                        </span>

                                        <span className="role-select">
                                            {role === key ? (
                                                <>
                                                    <CheckCircle2 size={16} />
                                                    Selected
                                                </>
                                            ) : (
                                                <>
                                                    Choose view
                                                    <ArrowUpRight size={15} />
                                                </>
                                            )}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>

                        <div className="project-entry">

                            <div className="project-entry-heading">
                                <span className="entry-icon">
                                    <FolderKanban size={19} />
                                </span>

                                <div>
                                    <h3>Open a project</h3>
                                    <p>
                                        Enter the project ID used by your
                                        existing InfraSync backend.
                                    </p>
                                </div>
                            </div>

                            <form
                                onSubmit={openProject}
                                className="project-form"
                            >
                                <label htmlFor="project-id">
                                    Project ID
                                </label>

                                <div className="input-row">
                                    <input
                                        id="project-id"
                                        value={projectId}
                                        onChange={(e) =>
                                            setProjectId(e.target.value)
                                        }
                                        placeholder="Enter project ID"
                                        required
                                    />

                                    <button
                                        type="submit"
                                        disabled={!projectId.trim()}
                                    >
                                        Continue
                                        <ArrowUpRight size={16} />
                                    </button>
                                </div>
                            </form>

                            {role === "manager" && (
                                <button
                                    className="dashboard-link"
                                    onClick={openDashboard}
                                >
                                    <LayoutDashboard size={16} />
                                    Open manager dashboard
                                    <ArrowUpRight size={15} />
                                </button>
                            )}

                            <p className="note">
                                <ShieldCheck size={14} />
                                Existing Flask project functionality is
                                preserved.
                            </p>

                        </div>
                    </section>

                    <footer className="footer">
                        <span>INFRASYNC AI</span>
                        <span>Role-based project workspace</span>
                    </footer>

                </main>
            )}

            {/* REACT MANAGER DASHBOARD */}
            {activePage === "manager-dashboard" && (
                <main className="workspace-page">

                    <div className="workspace-toolbar">
                        <button
                            className="back-button"
                            onClick={goHome}
                        >
                            <ArrowLeft size={16} />
                            Back to role selection
                        </button>
                    </div>

                    <ManagerDashboard
                        projects={projects}
                        loading={loading}
                        error={error}
                        onRefresh={loadProjects}
                    />

                </main>
            )}

            {/* EXISTING FLASK PROJECT PAGE */}
            {activePage === "flask-project" && (
    <main className="workspace-page">
        <div className="workspace-toolbar">
            <button className="back-button" onClick={goHome}>
                <ArrowLeft size={16} />
                Back to role selection
            </button>
        </div>

        <ProjectDetails projectId={projectId} />
    </main>
)}

        </div>
    );
}

export default App;