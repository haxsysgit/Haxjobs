<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchHealthStatus, fetchHermesTasks, fetchJobs, fetchProfiles } from '@/services/api'

const healthStatus = ref('checking')
const healthMessage = ref('Checking backend connection…')
const jobs = ref([])
const profiles = ref([])
const hermesTasks = ref([])
const loadingError = ref('')

const pipelineSteps = [
  { label: 'Capture', caption: 'Save job', state: 'live' },
  { label: 'Analyze', caption: 'Hermes task', state: 'next' },
  { label: 'Generate pack', caption: 'CV + cover', state: 'soon' },
  { label: 'Review', caption: 'Approval gate', state: 'soon' },
  { label: 'Outreach', caption: 'Draft only', state: 'later' },
]

const statCards = computed(() => [
  { label: 'saved jobs', value: jobs.value.length, accent: 'cyan', detail: 'manual captures ready for Hermes' },
  { label: 'profiles', value: profiles.value.length, accent: 'violet', detail: 'truth records Hermes can reuse' },
  { label: 'Hermes tasks', value: hermesTasks.value.length, accent: 'green', detail: 'queued work for 0.2.x' },
])

const recentJobs = computed(() => jobs.value.slice(0, 5))
const activeJobs = computed(() => jobs.value.length || 1)
const profileCoverage = computed(() => Math.min(100, profiles.value.length * 35))
const taskPulse = computed(() => Math.min(100, hermesTasks.value.length * 28))

function formatCount(value, label) {
  return `${value} ${value === 1 ? label.slice(0, -1) : label}`
}

onMounted(async () => {
  try {
    const [health, savedJobs, savedProfiles, tasks] = await Promise.all([
      fetchHealthStatus(),
      fetchJobs(),
      fetchProfiles(),
      fetchHermesTasks(),
    ])

    healthStatus.value = health.status
    healthMessage.value = `${health.service} is online`
    jobs.value = savedJobs
    profiles.value = savedProfiles
    hermesTasks.value = tasks
  } catch (error) {
    healthStatus.value = 'offline'
    healthMessage.value = 'Backend is not reachable yet'
    loadingError.value = 'HaxJobs could not load dashboard data from the backend yet.'
    console.error(error)
  }
})
</script>

<template>
  <main class="home-view shell-page">
    <section class="hero-grid">
      <article class="hero-card hax-card">
        <div class="hero-copy">
          <p class="eyebrow">HaxJobs 0.1.7 · UI identity pass</p>
          <h1><span class="gradient-text">Your job-search cockpit,</span> wired for Hermes.</h1>
          <p class="summary">
            Not another spreadsheet clone. HaxJobs is the visual surface where jobs, profile truth, packs, approvals, and Hermes work requests become one living workflow.
          </p>

          <div class="hero-actions">
            <RouterLink class="primary-button" to="/jobs">Save a job</RouterLink>
            <RouterLink class="ghost-button" to="/profiles">Inspect profile truth</RouterLink>
          </div>

          <div class="health-pill" :data-status="healthStatus">
            <span class="status-dot"></span>
            {{ healthMessage }}
          </div>
          <p v-if="loadingError" class="error-copy">{{ loadingError }}</p>
        </div>

        <div class="orbit-console" aria-label="Hermes workflow orbit visual">
          <div class="orbit-ring ring-one"></div>
          <div class="orbit-ring ring-two"></div>
          <div class="orbit-core">
            <strong>Hermes</strong>
            <span>reasoning core</span>
          </div>
          <span class="orbit-node node-jobs">Jobs</span>
          <span class="orbit-node node-profile">Profile</span>
          <span class="orbit-node node-packs">Packs</span>
          <span class="orbit-node node-approval">Review</span>
        </div>
      </article>

      <aside class="mission-card hax-card">
        <p class="eyebrow">Today’s readiness</p>
        <div class="radial-meter" :style="{ '--meter': `${Math.min(96, activeJobs * 18 + profileCoverage / 2 + taskPulse / 4)}%` }">
          <span>{{ Math.min(96, activeJobs * 18 + Math.round(profileCoverage / 2) + Math.round(taskPulse / 4)) }}%</span>
        </div>
        <p class="mission-copy">Local system is ready for real job capture. 0.2.x turns the task queue into actual Hermes execution.</p>
      </aside>
    </section>

    <section class="stats-grid">
      <article v-for="stat in statCards" :key="stat.label" class="stat-card hax-card" :data-accent="stat.accent">
        <p class="stat-value">{{ stat.value }}</p>
        <p class="stat-label">{{ formatCount(stat.value, stat.label) }}</p>
        <small>{{ stat.detail }}</small>
      </article>
    </section>

    <section class="pipeline-card hax-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Live pipeline map</p>
          <h2>Built now, expanding into 0.2.x</h2>
        </div>
        <span class="pill">Human approval stays final</span>
      </div>

      <div class="pipeline-rail">
        <div v-for="step in pipelineSteps" :key="step.label" class="pipeline-step" :data-state="step.state">
          <span class="step-node"></span>
          <strong>{{ step.label }}</strong>
          <small>{{ step.caption }}</small>
        </div>
      </div>
    </section>

    <section class="panel-grid">
      <article class="panel-card hax-card">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">Recent saved jobs</p>
            <h2>Inbox signal</h2>
          </div>
          <span class="pill">{{ formatCount(jobs.length, 'saved jobs') }}</span>
        </div>

        <ul v-if="recentJobs.length" class="job-list">
          <li v-for="job in recentJobs" :key="job.id" class="job-row">
            <span class="job-index">{{ job.company?.slice(0, 2).toUpperCase() || 'HX' }}</span>
            <div>
              <h3>{{ job.title }}</h3>
              <p>{{ job.company }}</p>
            </div>
            <span class="job-status">{{ job.status }}</span>
          </li>
        </ul>
        <p v-else class="empty-copy">No jobs saved yet. Open Jobs and capture the first real target.</p>
      </article>

      <article class="panel-card hax-card handoff-card">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">Hermes handoff</p>
            <h2>Control room → worker brain → writeback</h2>
          </div>
        </div>

        <ul class="handoff-list">
          <li><span>01</span>HaxJobs stores the job, profile, pack, and task state.</li>
          <li><span>02</span>Hermes takes a structured task, reasons, and produces a result.</li>
          <li><span>03</span>HaxJobs receives the writeback and keeps review gates visible.</li>
        </ul>
      </article>
    </section>
  </main>
</template>

<style scoped>
.home-view {
  display: grid;
  gap: 1.2rem;
  padding-bottom: 8rem;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 1.2rem;
}

.hero-card {
  min-height: 460px;
  padding: clamp(1.3rem, 4vw, 3rem);
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.75fr);
  align-items: center;
  gap: 2rem;
  animation: slide-up 420ms ease both;
}

h1 {
  margin: 0;
  max-width: 13ch;
  font-size: clamp(3rem, 8vw, 6.8rem);
  line-height: 0.86;
  letter-spacing: -0.075em;
}

.summary {
  margin: 1.3rem 0 1.5rem;
  color: var(--text-soft);
  font-size: clamp(1rem, 2vw, 1.18rem);
  line-height: 1.7;
  max-width: 62ch;
}

.hero-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1.1rem;
}

.hero-actions a {
  text-decoration: none;
}

.health-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  width: fit-content;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--text-soft);
  padding: 0.65rem 0.8rem;
}

.status-dot {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 999px;
  background: var(--warning);
  box-shadow: 0 0 18px var(--warning);
}

.health-pill[data-status='ok'] .status-dot {
  background: var(--accent-3);
  box-shadow: 0 0 18px var(--accent-3);
}

.health-pill[data-status='offline'] .status-dot {
  background: var(--danger);
  box-shadow: 0 0 18px var(--danger);
}

.orbit-console {
  position: relative;
  min-height: 360px;
  display: grid;
  place-items: center;
}

.orbit-ring {
  position: absolute;
  border: 1px solid var(--border);
  border-radius: 999px;
  animation: pulse-ring 4.5s ease-in-out infinite;
}

.ring-one {
  width: 270px;
  height: 270px;
}

.ring-two {
  width: 190px;
  height: 190px;
  animation-delay: -1.4s;
}

.orbit-core {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 8.4rem;
  height: 8.4rem;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: white;
  box-shadow: var(--glow);
  text-align: center;
}

.orbit-core strong,
.orbit-core span {
  display: block;
}

.orbit-core span {
  max-width: 7ch;
  font-size: 0.7rem;
  opacity: 0.8;
}

.orbit-node {
  position: absolute;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--glass);
  color: var(--text-soft);
  padding: 0.55rem 0.75rem;
  box-shadow: var(--shadow);
  animation: floaty 5s ease-in-out infinite;
}

.node-jobs { top: 2rem; left: 3.2rem; }
.node-profile { top: 4.5rem; right: 1rem; animation-delay: -1s; }
.node-packs { bottom: 4.8rem; left: 1rem; animation-delay: -2s; }
.node-approval { bottom: 2.2rem; right: 3rem; animation-delay: -3s; }

.mission-card {
  padding: 1.25rem;
  display: grid;
  align-content: center;
  justify-items: center;
  text-align: center;
  animation: slide-up 520ms ease both;
}

.radial-meter {
  width: 11rem;
  height: 11rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, var(--bg) 0 54%, transparent 55%),
    conic-gradient(var(--accent-2) var(--meter), var(--surface-soft) 0);
  box-shadow: inset 0 0 34px rgb(0 0 0 / 18%), var(--glow);
}

.radial-meter span {
  font-size: 2.1rem;
  font-weight: 900;
}

.mission-copy {
  color: var(--text-soft);
  line-height: 1.6;
}

.stats-grid,
.panel-grid {
  display: grid;
  gap: 1.2rem;
}

.stats-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.panel-grid {
  grid-template-columns: 1fr 1fr;
}

.stat-card,
.panel-card,
.pipeline-card {
  padding: 1.25rem;
  animation: slide-up 560ms ease both;
}

.stat-value {
  margin: 0;
  font-size: 3rem;
  line-height: 0.9;
  font-weight: 900;
}

.stat-label {
  margin: 0.65rem 0 0.3rem;
  color: var(--text);
  font-weight: 800;
}

.stat-card small {
  color: var(--muted);
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.panel-heading h2 {
  margin: 0;
  font-size: clamp(1.4rem, 2vw, 2rem);
  letter-spacing: -0.04em;
}

.pipeline-rail {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75rem;
  margin-top: 1.4rem;
}

.pipeline-step {
  position: relative;
  min-height: 130px;
  border: 1px solid var(--border-soft);
  border-radius: 22px;
  background: var(--surface-soft);
  padding: 1rem;
  display: grid;
  align-content: space-between;
  transition: transform 180ms ease, background 180ms ease;
}

.pipeline-step:hover {
  transform: translateY(-4px);
  background: var(--surface-strong);
}

.step-node {
  width: 1rem;
  height: 1rem;
  border-radius: 999px;
  background: var(--muted);
  box-shadow: 0 0 18px var(--muted);
}

.pipeline-step[data-state='live'] .step-node { background: var(--accent-3); box-shadow: 0 0 18px var(--accent-3); }
.pipeline-step[data-state='next'] .step-node { background: var(--accent-2); box-shadow: 0 0 18px var(--accent-2); }
.pipeline-step strong { font-size: 1.05rem; }
.pipeline-step small { color: var(--muted); }

.job-list,
.handoff-list {
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
}

.job-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 1rem;
  padding: 0.9rem;
  border: 1px solid var(--border-soft);
  border-radius: 18px;
  background: var(--surface-soft);
  margin-top: 0.75rem;
}

.job-index {
  display: grid;
  place-items: center;
  width: 2.45rem;
  height: 2.45rem;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: white;
  font-family: var(--font-mono);
  font-weight: 900;
}

.job-row h3,
.job-row p {
  margin: 0;
}

.job-row p,
.empty-copy {
  color: var(--text-soft);
}

.job-status {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.45rem 0.7rem;
  color: var(--text-soft);
  text-transform: capitalize;
}

.handoff-list li {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.75rem;
  align-items: start;
  margin-top: 1rem;
  color: var(--text-soft);
  line-height: 1.6;
}

.handoff-list span {
  color: var(--accent-2);
  font-family: var(--font-mono);
}

.error-copy {
  color: var(--danger);
}

@media (max-width: 1080px) {
  .hero-grid,
  .hero-card,
  .panel-grid {
    grid-template-columns: 1fr;
  }

  .mission-card {
    min-height: 280px;
  }
}

@media (max-width: 780px) {
  .stats-grid,
  .pipeline-rail {
    grid-template-columns: 1fr;
  }

  .orbit-console {
    min-height: 300px;
  }
}
</style>
