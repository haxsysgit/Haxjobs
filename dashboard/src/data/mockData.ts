export interface Job {
  id: string
  company: string
  title: string
  location: string
  source: string
  fitScore: number
  level: 1 | 2 | 3 | 4 | 5
  levelName: string
  status: 'completed' | 'evaluating' | 'pending' | 'weak_fit' | 'skipped'
  strongestMatches: string[]
  majorGaps: string[]
  sponsorshipRisk: string
  summary: string
  applicationUrl: string
  packDir: string
  receivedAt: string
  processedAt: string | null
}

export interface ActivityEvent {
  id: string
  time: string
  type: 'job_found' | 'evaluated' | 'pack_generated' | 'email_sent' | 'scraper_run' | 'pipeline_scan'
  message: string
  detail?: string
}

export const mockJobs: Job[] = [
  {
    id: '1',
    company: 'Spotify',
    title: 'Backend Engineer - Release',
    location: 'London, UK',
    source: 'lever_api',
    fitScore: 82,
    level: 1,
    levelName: 'Standard',
    status: 'completed',
    strongestMatches: ['FastAPI experience at Vigilis', 'PostgreSQL depth', 'Docker in production'],
    majorGaps: ['No Kubernetes production ownership', 'AWS depth unconfirmed'],
    sponsorshipRisk: 'medium',
    summary: 'Strong backend match. Direct FastAPI and PostgreSQL experience aligns with Spotify stack. Main gaps are Kubernetes depth and cloud platform ownership.',
    applicationUrl: 'https://jobs.lever.co/spotify/830106b6-0055-4003-bcaa-370648915622/apply',
    packDir: '/home/hermes/job-pipeline/packs/Spotify_Backend_Engineer_Release',
    receivedAt: '2026-06-06T14:30:00Z',
    processedAt: '2026-06-06T15:45:00Z'
  },
  {
    id: '2',
    company: 'Palantir',
    title: 'Forward Deployed AI Engineer',
    location: 'London, UK',
    source: 'lever_api',
    fitScore: 78,
    level: 2,
    levelName: 'Quick Apply',
    status: 'completed',
    strongestMatches: ['AI workflow experience (Haxaml)', 'Python backend depth', 'LLM integration'],
    majorGaps: ['No security clearance', 'No consulting/client-facing experience'],
    sponsorshipRisk: 'high',
    summary: 'Good AI engineering fit. Haxaml and LLM work are directly relevant. Palantir may require security clearance.',
    applicationUrl: 'https://jobs.lever.co/palantir/abc123',
    packDir: '/home/hermes/job-pipeline/packs/Palantir_Forward_Deployed_AI_Engineer',
    receivedAt: '2026-06-06T16:00:00Z',
    processedAt: '2026-06-06T17:20:00Z'
  },
  {
    id: '3',
    company: 'Monzo',
    title: 'Backend Engineer - Core Banking',
    location: 'London, UK',
    source: 'lever_api',
    fitScore: 85,
    level: 1,
    levelName: 'Standard',
    status: 'completed',
    strongestMatches: ['Python/PostgreSQL stack match', 'RBAC and auth experience', 'Production backend ownership'],
    majorGaps: ['No fintech domain experience', 'No Go experience (nice-to-have)'],
    sponsorshipRisk: 'low',
    summary: 'Excellent fit for Monzo backend role. Core stack is identical to experience. Fintech domain is learnable.',
    applicationUrl: 'https://jobs.lever.co/monzo/def456',
    packDir: '/home/hermes/job-pipeline/packs/Monzo_Backend_Engineer_Core',
    receivedAt: '2026-06-07T08:15:00Z',
    processedAt: '2026-06-07T09:30:00Z'
  },
  {
    id: '4',
    company: 'Skin + Me',
    title: 'Backend Engineer (Python)',
    location: 'London, UK · Hybrid',
    source: 'jsearch_api',
    fitScore: 88,
    level: 1,
    levelName: 'Standard',
    status: 'completed',
    strongestMatches: ['Python/Flask/SQLAlchemy stack', 'E-commerce/order systems experience', 'Docker + CI/CD'],
    majorGaps: ['AWS production experience', 'No React depth'],
    sponsorshipRisk: 'low',
    summary: 'Very strong fit. Stack nearly identical to Vigilis/Pharmax experience. Python, SQLAlchemy, MySQL, Docker all match.',
    applicationUrl: 'https://apply.workable.com/skinandme/j/ACB925B91E',
    packDir: '/home/hermes/job-pipeline/packs/Skin_Me_Backend_Engineer',
    receivedAt: '2026-06-07T07:00:00Z',
    processedAt: '2026-06-07T08:10:00Z'
  },
  {
    id: '5',
    company: 'UK Tech Company',
    title: 'Python Developer',
    location: 'London, UK',
    source: 'manual',
    fitScore: 89,
    level: 1,
    levelName: 'Standard',
    status: 'completed',
    strongestMatches: ['FastAPI + PostgreSQL depth', 'SQLAlchemy + Alembic', 'pytest discipline'],
    majorGaps: ['Kubernetes production', 'Cloud platform ownership', 'React depth'],
    sponsorshipRisk: 'medium',
    summary: 'Strong backend match. FastAPI and PostgreSQL experience directly relevant. Gaps are cloud/K8s depth.',
    applicationUrl: '',
    packDir: '/home/hermes/job-pipeline/packs/UK_Tech_Company_Python_Developer',
    receivedAt: '2026-06-04T16:34:00Z',
    processedAt: '2026-06-04T16:42:00Z'
  },
]

export const mockActivity: ActivityEvent[] = [
  { id: 'a1', time: '09:30', type: 'scraper_run', message: 'Lever scraper completed', detail: '19 companies checked · 2 new jobs found' },
  { id: 'a2', time: '09:32', type: 'job_found', message: 'New job discovered', detail: 'Backend Engineer at Monzo (85%)' },
  { id: 'a3', time: '09:35', type: 'evaluated', message: 'Fit evaluation complete', detail: 'Monzo scored 85% — Standard pack generated' },
  { id: 'a4', time: '09:36', type: 'pack_generated', message: 'Pack generated', detail: 'Level 1 Standard pack for Monzo' },
  { id: 'a5', time: '09:37', type: 'email_sent', message: 'Email sent to Arinze', detail: 'Fit report + CV + cover letter for Monzo (85%)' },
  { id: 'a6', time: '08:10', type: 'pack_generated', message: 'Pack generated', detail: 'Level 1 Standard pack for Skin + Me (88%)' },
  { id: 'a7', time: '08:10', type: 'email_sent', message: 'Email sent to Arinze', detail: 'Fit report + CV + cover letter for Skin + Me (88%)' },
  { id: 'a8', time: '08:00', type: 'scraper_run', message: 'JSearch API scan completed', detail: '3 new roles found, 1 met threshold' },
  { id: 'a9', time: '07:00', type: 'pipeline_scan', message: 'Pipeline scan completed', detail: '0 pending jobs in queue' },
  { id: 'a10', time: '00:00', type: 'scraper_run', message: 'Ashby scraper completed', detail: '60 companies checked · 4 new jobs found' },
]

export const mockCompanies = [
  { name: 'Spotify', source: 'lever', jobCount: 12, lastRun: '09:30 today' },
  { name: 'Monzo', source: 'lever', jobCount: 8, lastRun: '09:30 today' },
  { name: 'Revolut', source: 'lever', jobCount: 15, lastRun: '09:30 today' },
  { name: 'Cloudflare', source: 'lever', jobCount: 6, lastRun: '09:30 today' },
  { name: 'Palantir', source: 'lever', jobCount: 4, lastRun: '09:30 today' },
  { name: 'Vercel', source: 'ashby', jobCount: 9, lastRun: '00:00 today' },
  { name: 'Linear', source: 'ashby', jobCount: 3, lastRun: '00:00 today' },
  { name: 'Docker', source: 'ashby', jobCount: 7, lastRun: '00:00 today' },
  { name: 'Snowflake', source: 'ashby', jobCount: 11, lastRun: '00:00 today' },
  { name: 'Hugging Face', source: 'ashby', jobCount: 5, lastRun: '00:00 today' },
  { name: 'Wise', source: 'greenhouse', jobCount: 10, lastRun: 'yesterday' },
  { name: 'GitLab', source: 'greenhouse', jobCount: 14, lastRun: 'yesterday' },
  { name: 'Anthropic', source: 'greenhouse', jobCount: 6, lastRun: 'yesterday' },
  { name: 'DeepMind', source: 'greenhouse', jobCount: 8, lastRun: 'yesterday' },
]
