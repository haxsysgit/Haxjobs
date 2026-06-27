import { useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation, useParams } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Pipeline } from './pages/Pipeline'
import { JobDetailPage } from './pages/JobDetail'
import { Activity } from './pages/Activity'
import { Profile } from './pages/Profile'
import { Discovery } from './pages/Discovery'
import { Outreach } from './pages/Outreach'
import { Settings } from './pages/Settings'
import { PacksPage } from './pages/Packs'
import { Whitelist } from './pages/WhitelistPage'
import { ToastProvider } from './components/Toasts'
import { useToast } from './components/useToast'
import { useApiData } from './data/useApiData'
import { Home, Layers, Activity as ActivityIcon, User, Globe, Send, Settings as SettingsIcon, ChevronLeft, ChevronRight, FileText, CheckCircle } from './components/Icons'
import { api, type Job } from './data/api'
import './theme.css'

// HaxJobs version — exposed on window for debugging
declare global {
  interface Window {
    __HAXJOBS_VERSION__?: string
  }
}
window.__HAXJOBS_VERSION__ = '3.0.0'

// ── Sidebar ──

type ViewKey = 'dashboard' | 'jobs' | 'packs' | 'whitelist' | 'activity' | 'profile' | 'discovery' | 'outreach' | 'settings'

const navItems: { key: ViewKey; label: string; Icon: React.FC<{ size?: number }>; path: string }[] = [
  { key: 'dashboard', label: 'Dashboard', Icon: Home, path: '/' },
  { key: 'jobs', label: 'Jobs', Icon: Layers, path: '/jobs' },
  { key: 'packs', label: 'Packs', Icon: FileText, path: '/packs' },
  { key: 'whitelist', label: 'Whitelist', Icon: CheckCircle, path: '/whitelist' },
  { key: 'activity', label: 'Activity', Icon: ActivityIcon, path: '/activity' },
  { key: 'profile', label: 'Profile', Icon: User, path: '/profile' },
  { key: 'discovery', label: 'Discovery', Icon: Globe, path: '/discovery' },
  { key: 'outreach', label: 'Outreach', Icon: Send, path: '/outreach' },
  { key: 'settings', label: 'Settings', Icon: SettingsIcon, path: '/settings' },
]

function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const { jobs, discovery, profile, connected, updateJob } = useApiData()
  const toast = useToast()

  const activeCount = jobs.filter(j => j.fitScore > 0).length
  const userName = profile?.name || 'Arinze'
  const userInitial = userName.charAt(0).toUpperCase()

  const currentNav =
    navItems.find(n => n.path !== '/' && location.pathname.startsWith(n.path)) || navItems[0]
  const pageTitle = currentNav.label

  const handleUnskip = async (job: Job) => {
    try {
      await api.unskipJob(job.id, 'User unskipped from dashboard')
      updateJob(job.id, { status: 'pending' })
      toast.success(`Unskipped: ${job.title.slice(0, 40)}`)
    } catch { toast.error('Failed to unskip job') }
  }

  const handleApprove = async (job: Job) => {
    try {
      await api.approveJob(job.id, 'User approved from dashboard')
      updateJob(job.id, { status: 'approved' })
      toast.success(`Approved: ${job.title.slice(0, 40)}`)
    } catch { toast.error('Failed to approve job') }
  }

  return (
    <>
      <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
        <div className="sidebar-brand">
          <div className="logo">{userInitial}</div>
          <span className="name">{userName.split(' ')[0]}</span>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(({ key, label, Icon, path }) => (
            <a key={key} href={path}
              className={location.pathname === path || (path !== '/' && location.pathname.startsWith(path)) ? 'active' : ''}
              onClick={e => { e.preventDefault(); navigate(path) }}>
              <Icon size={18} /><span>{label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="btn btn-ghost"
            style={{ width: '100%', justifyContent: collapsed ? 'center' : 'flex-start' }}
            onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      <div className="main">
        <div className="topbar">
          <h2>{pageTitle}</h2>
          <div className="topbar-actions">
            <span style={{ fontSize: 12, color: connected ? 'var(--success)' : 'var(--muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 999, background: connected ? 'var(--success)' : 'var(--muted)', display: 'inline-block' }} />
              {connected ? `Connected · ${activeCount} active` : 'API offline'}
            </span>
          </div>
        </div>
        <div className="page">
          <Routes>
            <Route path="/" element={<Dashboard jobs={jobs} discovery={discovery} connected={connected} />} />
            <Route path="/jobs" element={<Pipeline jobs={jobs} connected={connected} onUnskip={handleUnskip} onApprove={handleApprove} />} />
            <Route path="/jobs/:id" element={<JobDetailRoute jobs={jobs} />} />
            <Route path="/packs" element={<PacksPage connected={connected} />} />
            <Route path="/whitelist" element={<Whitelist connected={connected} />} />
            <Route path="/activity" element={<Activity connected={connected} />} />
            <Route path="/profile" element={<Profile data={profile} />} />
            <Route path="/discovery" element={<Discovery data={discovery} connected={connected} />} />
            <Route path="/outreach" element={<Outreach />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </>
  )
}

// Route wrapper to get job by ID from params
function JobDetailRoute({ jobs }: { jobs: Job[] }) {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const job = jobs.find(j => j.id === id)
  if (!job) {
    return (
      <div className="empty">
        <h3>Job not found</h3>
        <button className="btn" onClick={() => navigate('/jobs')}>Back to Jobs</button>
      </div>
    )
  }
  return <JobDetailPage job={job} onBack={() => navigate('/jobs')} />
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AppLayout />
      </ToastProvider>
    </BrowserRouter>
  )
}
