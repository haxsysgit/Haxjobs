<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchHealthStatus, fetchHermesTasks, fetchJobs, fetchProfiles } from '@/services/api'

const healthStatus = ref('checking')
const healthMessage = ref('Checking backend connection…')
const jobs = ref([])
const profiles = ref([])
const hermesTasks = ref([])
const loadingError = ref('')

const stats = computed(() => [
  {
    label: 'saved jobs',
    value: jobs.value.length,
  },
  {
    label: 'profiles',
    value: profiles.value.length,
  },
  {
    label: 'Hermes tasks',
    value: hermesTasks.value.length,
  },
])

const recentJobs = computed(() => jobs.value.slice(0, 5))

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
  <main class="home-view">
    <section class="hero-card">
      <p class="eyebrow">HaxJobs 0.1.6</p>
      <h1>Hermes-powered job search starts here.</h1>
      <p class="summary">
        HaxJobs is the UI and workflow layer for the Hermes job application pipeline. This slice makes the starter dashboard read real backend data instead of only checking health.
      </p>

      <div class="health-pill" :data-status="healthStatus">
        {{ healthMessage }}
      </div>

      <p v-if="loadingError" class="error-copy">{{ loadingError }}</p>
    </section>

    <section class="stats-grid">
      <article v-for="stat in stats" :key="stat.label" class="stat-card">
        <p class="stat-value">{{ stat.value }}</p>
        <p class="stat-label">{{ formatCount(stat.value, stat.label) }}</p>
      </article>
    </section>

    <section class="panel-grid">
      <article class="panel-card">
        <div class="panel-heading">
          <h2>Recent saved jobs</h2>
          <span>{{ formatCount(jobs.length, 'saved jobs') }}</span>
        </div>

        <ul v-if="recentJobs.length" class="job-list">
          <li v-for="job in recentJobs" :key="job.id" class="job-row">
            <div>
              <h3>{{ job.title }}</h3>
              <p>{{ job.company }}</p>
            </div>
            <span class="job-status">{{ job.status }}</span>
          </li>
        </ul>
        <p v-else class="empty-copy">No jobs saved yet. The next slice will let you add them from the UI.</p>
      </article>

      <article class="panel-card">
        <div class="panel-heading">
          <h2>Hermes handoff</h2>
        </div>

        <ul class="handoff-list">
          <li>HaxJobs stores the job, profile, pack, and task state.</li>
          <li>Hermes reads or receives a task request, does the heavy reasoning, then writes structured results back.</li>
          <li>Approval gates stay in HaxJobs so you can review before risky actions.</li>
        </ul>
      </article>
    </section>
  </main>
</template>

<style scoped>
.home-view {
  min-height: calc(100vh - 72px);
  padding: 2rem;
  display: grid;
  gap: 1.5rem;
  color: #eef4ff;
}

.hero-card,
.stat-card,
.panel-card {
  border: 1px solid #273244;
  border-radius: 24px;
  background: #101827;
  box-shadow: 0 24px 80px rgb(0 0 0 / 24%);
}

.hero-card {
  padding: 2rem;
}

.eyebrow {
  margin: 0 0 0.75rem;
  color: #7dd3fc;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1;
}

.summary {
  margin: 1rem 0 1.5rem;
  color: #bfd0e8;
  font-size: 1.05rem;
  max-width: 72ch;
}

.health-pill {
  display: inline-flex;
  padding: 0.7rem 1rem;
  border-radius: 999px;
  background: #172033;
  color: #d8e6ff;
  font-weight: 700;
}

.health-pill[data-status='ok'] {
  background: #064e3b;
  color: #d1fae5;
}

.health-pill[data-status='offline'] {
  background: #7f1d1d;
  color: #fee2e2;
}

.error-copy,
.empty-copy {
  margin: 1rem 0 0;
  color: #fca5a5;
}

.stats-grid,
.panel-grid {
  display: grid;
  gap: 1rem;
}

.stats-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.panel-grid {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

.stat-card,
.panel-card {
  padding: 1.5rem;
}

.stat-value {
  margin: 0;
  font-size: 2rem;
  font-weight: 800;
}

.stat-label {
  margin: 0.5rem 0 0;
  color: #bfd0e8;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.panel-heading h2 {
  margin: 0;
}

.job-list,
.handoff-list {
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
}

.job-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 0;
  border-top: 1px solid #1f2937;
}

.job-row:first-child {
  border-top: 0;
  padding-top: 0;
}

.job-row h3 {
  margin: 0;
  font-size: 1rem;
}

.job-row p {
  margin: 0.35rem 0 0;
  color: #bfd0e8;
}

.job-status {
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  background: #172033;
  color: #d8e6ff;
  text-transform: capitalize;
  font-size: 0.9rem;
}

.handoff-list li {
  margin-top: 0.9rem;
  color: #d8e6ff;
}

.handoff-list li:first-child {
  margin-top: 0;
}
</style>
