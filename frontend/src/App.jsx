import { useMemo, useState } from 'react'
import { Activity, ArrowLeft, ArrowUpRight, BriefcaseBusiness, CheckCircle2, ClipboardList, ExternalLink, FolderKanban, LayoutDashboard, ShieldCheck, Users, UserRound, Building2 } from 'lucide-react'

const FLASK_BASE = import.meta.env.VITE_FLASK_BASE_URL || ''

const roleInfo = {
  manager: {
    title: 'Manager workspace',
    subtitle: 'Monitor projects, coordinate teams, and manage delivery.',
    icon: BriefcaseBusiness,
    actions: [
      { title: 'Project dashboard', description: 'Open your existing project dashboard and portfolio summary.', href: '/dashboard', icon: LayoutDashboard },
    ],
    projectView: 'manager'
  },
  employee: {
    title: 'Employee workspace',
    subtitle: 'Review your assigned work and follow project progress.',
    icon: UserRound,
    actions: [],
    projectView: 'employee'
  },
  client: {
    title: 'Client workspace',
    subtitle: 'View project progress, tasks, and risk information.',
    icon: Building2,
    actions: [],
    projectView: 'client'
  }
}

function App() {
  const [role, setRole] = useState('manager')
  const [projectId, setProjectId] = useState('')
  const [activeUrl, setActiveUrl] = useState('')
  const [showWorkspace, setShowWorkspace] = useState(false)
  const selected = roleInfo[role]
  const RoleIcon = selected.icon

  const projectUrl = useMemo(() => {
    const id = projectId.trim()
    return id ? `/project/${encodeURIComponent(id)}?view=${selected.projectView}` : ''
  }, [projectId, selected.projectView])

  function openProject(event) {
    event.preventDefault()
    if (!projectUrl) return
    setActiveUrl(projectUrl)
    setShowWorkspace(true)
  }

  function openDashboard() {
    setActiveUrl('/dashboard')
    setShowWorkspace(true)
  }

  function goHome() {
    setShowWorkspace(false)
    setActiveUrl('')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={goHome} aria-label="InfraSync home">
          <span className="brand-mark"><Activity size={21} /></span>
          <span>InfraSync <b>AI</b></span>
        </button>
        <div className="topbar-right"><span className="status-dot" /> Backend connection configured</div>
      </header>

      {showWorkspace ? (
        <main className="workspace-page">
          <div className="workspace-toolbar">
            <button className="back-button" onClick={goHome}><ArrowLeft size={16} /> Back to role selection</button>
            <a className="open-new" href={`${FLASK_BASE}${activeUrl}`} target="_blank" rel="noreferrer">Open page separately <ExternalLink size={15} /></a>
          </div>
          <div className="workspace-heading">
            <div><span className="eyebrow">{role.toUpperCase()} VIEW</span><h1>{selected.title}</h1></div>
            <span className="secure-label"><ShieldCheck size={15} /> Existing Flask functionality</span>
          </div>
          <div className="frame-wrap">
            <iframe title={`${selected.title} - existing Flask page`} src={`${FLASK_BASE}${activeUrl}`} className="flask-frame" />
          </div>
        </main>
      ) : (
        <main className="home-page">
          <section className="hero">
            <div className="eyebrow"><span className="status-dot" /> PROJECT WORKFLOW PLATFORM</div>
            <h1>Project delivery,<br /><span>in sync.</span></h1>
            <p className="hero-copy">Choose your workspace to access the tools and project information relevant to your role.</p>
            <div className="hero-stats">
              <div><Activity size={17} /><span>Predictive risk monitoring</span></div>
              <div><ShieldCheck size={17} /><span>Existing backend preserved</span></div>
            </div>
          </section>

          <section className="portal">
            <div className="section-heading"><div><span className="eyebrow">WORKSPACE ACCESS</span><h2>Select your role</h2></div><span className="step-label">01 / 02</span></div>
            <div className="role-grid">
              {Object.entries(roleInfo).map(([key, info]) => {
                const Icon = info.icon
                return <button key={key} className={`role-card ${role === key ? 'selected' : ''}`} onClick={() => { setRole(key); setShowWorkspace(false) }}>
                  <span className="role-icon"><Icon size={22} /></span>
                  <span className="role-name">{key[0].toUpperCase() + key.slice(1)}</span>
                  <span className="role-description">{info.subtitle}</span>
                  <span className="role-select">{role === key ? <><CheckCircle2 size={16} /> Selected</> : <>Choose view <ArrowUpRight size={15} /></>}</span>
                </button>
              })}
            </div>

            <div className="project-entry">
              <div className="project-entry-heading">
                <span className="entry-icon"><FolderKanban size={19} /></span>
                <div><h3>Open a project</h3><p>Enter the project ID used by your existing InfraSync backend.</p></div>
              </div>
              <form onSubmit={openProject} className="project-form">
                <label htmlFor="project-id">Project ID</label>
                <div className="input-row">
                  <input id="project-id" value={projectId} onChange={e => setProjectId(e.target.value)} placeholder="Enter project ID" required />
                  <button type="submit" disabled={!projectId.trim()}>Continue <ArrowUpRight size={16} /></button>
                </div>
              </form>
              {role === 'manager' && <button className="dashboard-link" onClick={openDashboard}><LayoutDashboard size={16} /> Open manager dashboard <ArrowUpRight size={15} /></button>}
              <p className="note"><ShieldCheck size={14} /> This interface opens your existing Flask pages. It does not replace or modify your model, database, or business logic.</p>
            </div>
          </section>
          <footer className="footer"><span>INFRASYNC AI</span><span>Role-based project workspace</span></footer>
        </main>
      )}
    </div>
  )
}

export default App
