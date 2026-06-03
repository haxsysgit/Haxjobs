<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { createManualJob, fetchJobs } from '@/services/api'

const jobs = ref([])
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const selectedTemplate = ref('backend')

const captureTemplates = [
  { id: 'backend', label: 'Backend role', next_action: 'Analyze with Hermes', notes: 'Check backend depth, APIs, database, and sponsorship.' },
  { id: 'ai', label: 'AI role', next_action: 'Generate tailored AI pack', notes: 'Highlight RAG, evaluation, automation, and Python depth.' },
  { id: 'outreach', label: 'Outreach target', next_action: 'Find contact', notes: 'Look for hiring manager or recruiter before applying.' },
]

const form = reactive({
  company: '',
  title: '',
  location: '',
  source_platform: 'manual',
  source_url: '',
  job_description: '',
  next_action: 'Analyze with Hermes',
  notes: '',
})

const visibleJobs = computed(() => jobs.value.slice(0, 8))
const captureHealth = computed(() => Math.min(100, 18 + jobs.value.length * 14))

function applyTemplate(template) {
  selectedTemplate.value = template.id
  form.next_action = template.next_action
  form.notes = template.notes
}

async function loadJobs() {
  loading.value = true
  errorMessage.value = ''

  try {
    jobs.value = await fetchJobs()
  } catch (error) {
    errorMessage.value = 'Could not load saved jobs right now.'
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function saveJob() {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const savedJob = await createManualJob({
      company: form.company,
      title: form.title,
      location: form.location || null,
      source_platform: form.source_platform,
      source_url: form.source_url || null,
      job_description: form.job_description || null,
      next_action: form.next_action || null,
      notes: form.notes || null,
    })

    jobs.value = [savedJob, ...jobs.value]
    successMessage.value = `${savedJob.company} entered the cockpit.`
    form.company = ''
    form.title = ''
    form.location = ''
    form.source_platform = 'manual'
    form.source_url = ''
    form.job_description = ''
    form.next_action = 'Analyze with Hermes'
    form.notes = ''
  } catch (error) {
    errorMessage.value = 'Could not save the job yet. Check the backend and try again.'
    console.error(error)
  } finally {
    saving.value = false
  }
}

onMounted(loadJobs)
</script>

<template>
  <main class="jobs-view shell-page">
    <section class="jobs-hero hax-card">
      <div>
        <p class="eyebrow">Capture bay</p>
        <h1><span class="gradient-text">Turn job pages</span> into structured targets.</h1>
        <p>
          Manual capture is the bridge before browser extensions. Save real jobs here now, then 0.2.x lets Hermes pick them up for analysis and pack generation.
        </p>
      </div>
      <div class="capture-meter" :style="{ '--meter': `${captureHealth}%` }">
        <span>{{ jobs.length }}</span>
        <small>saved targets</small>
      </div>
    </section>

    <section class="jobs-layout">
      <article class="form-card hax-card">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">Manual save</p>
            <h2>Paste the signal, not the whole mess.</h2>
          </div>
        </div>

        <div class="template-strip" aria-label="Capture templates">
          <button
            v-for="template in captureTemplates"
            :key="template.id"
            :class="{ active: selectedTemplate === template.id }"
            type="button"
            @click="applyTemplate(template)"
          >
            {{ template.label }}
          </button>
        </div>

        <form data-test="job-form" class="job-form" @submit.prevent="saveJob">
          <label>
            Company
            <input data-test="company-input" v-model="form.company" required placeholder="Anthropic" />
          </label>

          <label>
            Role title
            <input data-test="title-input" v-model="form.title" required placeholder="Backend Engineer" />
          </label>

          <label>
            Source platform
            <input data-test="source-platform-input" v-model="form.source_platform" required placeholder="manual" />
          </label>

          <label>
            Location
            <input v-model="form.location" placeholder="London / Remote" />
          </label>

          <label class="wide">
            Source URL
            <input v-model="form.source_url" placeholder="https://company.com/jobs/123" />
          </label>

          <label class="wide">
            Next action
            <input v-model="form.next_action" placeholder="Analyze with Hermes" />
          </label>

          <label class="wide">
            Notes
            <textarea v-model="form.notes" rows="3" placeholder="Why this role matters, blockers, quick thoughts"></textarea>
          </label>

          <label class="wide">
            Job description
            <textarea v-model="form.job_description" rows="6" placeholder="Paste the job description here if you have it"></textarea>
          </label>

          <button class="primary-button" :disabled="saving" type="submit">
            {{ saving ? 'Saving signal…' : 'Save to cockpit' }}
          </button>
        </form>

        <p v-if="successMessage" class="success-copy">{{ successMessage }}</p>
        <p v-if="errorMessage" class="error-copy">{{ errorMessage }}</p>
      </article>

      <aside class="inbox-card hax-card">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">Inbox</p>
            <h2>Saved targets</h2>
          </div>
          <span class="pill">{{ jobs.length }}</span>
        </div>

        <p v-if="loading" class="muted-copy">Loading saved jobs…</p>
        <p v-else-if="!jobs.length" class="muted-copy">No jobs saved yet. Capture the first one and watch this turn into a pipeline.</p>

        <ul v-else class="job-stack">
          <li v-for="job in visibleJobs" :key="job.id" class="job-card-mini">
            <span class="company-glyph">{{ job.company?.slice(0, 2).toUpperCase() || 'HX' }}</span>
            <div>
              <h3>{{ job.title }}</h3>
              <p>{{ job.company }}</p>
              <small>{{ job.application?.next_action ?? 'Awaiting Hermes task' }}</small>
            </div>
            <span class="job-status">{{ job.application?.status ?? 'Saved' }}</span>
          </li>
        </ul>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.jobs-view {
  display: grid;
  gap: 1.2rem;
  padding-bottom: 8rem;
}

.jobs-hero {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 2rem;
  padding: clamp(1.4rem, 4vw, 2.5rem);
}

.jobs-hero h1 {
  margin: 0;
  max-width: 12ch;
  font-size: clamp(2.8rem, 7vw, 5.8rem);
  line-height: 0.9;
  letter-spacing: -0.07em;
}

.jobs-hero p:not(.eyebrow) {
  max-width: 66ch;
  color: var(--text-soft);
  line-height: 1.7;
}

.capture-meter {
  width: 9.5rem;
  height: 9.5rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, var(--bg) 0 55%, transparent 56%),
    conic-gradient(var(--accent-2) var(--meter), var(--surface-soft) 0);
  box-shadow: var(--glow);
}

.capture-meter span,
.capture-meter small {
  grid-area: 1 / 1;
}

.capture-meter span {
  transform: translateY(-0.45rem);
  font-size: 2.2rem;
  font-weight: 900;
}

.capture-meter small {
  transform: translateY(1.25rem);
  color: var(--muted);
}

.jobs-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
  gap: 1.2rem;
}

.form-card,
.inbox-card {
  padding: 1.25rem;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.panel-heading h2 {
  margin: 0;
  font-size: clamp(1.5rem, 3vw, 2.4rem);
  letter-spacing: -0.05em;
}

.template-strip {
  display: flex;
  gap: 0.55rem;
  flex-wrap: wrap;
  margin: 1.25rem 0;
}

.template-strip button {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--text-soft);
  padding: 0.65rem 0.8rem;
  cursor: pointer;
}

.template-strip button.active {
  background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 45%, transparent), color-mix(in srgb, var(--accent-2) 28%, transparent));
  color: var(--text);
}

.job-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

label {
  display: grid;
  gap: 0.45rem;
  color: var(--text-soft);
  font-size: 0.92rem;
  font-weight: 700;
}

input,
textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--surface-soft);
  color: var(--text);
  padding: 0.9rem 1rem;
  outline: none;
  transition: border-color 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

input:focus,
textarea:focus {
  border-color: color-mix(in srgb, var(--accent-2) 64%, var(--border));
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent-2) 12%, transparent);
}

.wide {
  grid-column: 1 / -1;
}

.success-copy { color: var(--accent-3); }
.error-copy { color: var(--danger); }
.muted-copy { color: var(--text-soft); }

.job-stack {
  display: grid;
  gap: 0.75rem;
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
}

.job-card-mini {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.8rem;
  align-items: center;
  border: 1px solid var(--border-soft);
  border-radius: 22px;
  background: var(--surface-soft);
  padding: 0.9rem;
  transition: transform 180ms ease, background 180ms ease;
}

.job-card-mini:hover {
  transform: translateY(-3px);
  background: var(--surface-strong);
}

.company-glyph {
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: white;
  font-family: var(--font-mono);
  font-weight: 900;
}

.job-card-mini h3,
.job-card-mini p,
.job-card-mini small {
  margin: 0;
}

.job-card-mini p,
.job-card-mini small {
  color: var(--muted);
}

.job-status {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.45rem 0.65rem;
  color: var(--text-soft);
}

@media (max-width: 980px) {
  .jobs-hero,
  .jobs-layout,
  .job-form {
    grid-template-columns: 1fr;
  }
}
</style>
