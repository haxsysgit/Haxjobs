<script setup>
import { onMounted, reactive, ref } from 'vue'

import { createManualJob, fetchJobs } from '@/services/api'

const jobs = ref([])
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const form = reactive({
  company: '',
  title: '',
  location: '',
  source_platform: 'manual',
  source_url: '',
  job_description: '',
  next_action: 'Generate pack',
  notes: '',
})

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
    successMessage.value = `${savedJob.company} was saved to HaxJobs.`
    form.company = ''
    form.title = ''
    form.location = ''
    form.source_platform = 'manual'
    form.source_url = ''
    form.job_description = ''
    form.next_action = 'Generate pack'
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
  <main class="jobs-view">
    <section class="panel-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Manual capture</p>
          <h1>Save a job from the UI</h1>
        </div>
      </div>

      <form data-test="job-form" class="job-form" @submit.prevent="saveJob">
        <label>
          Company
          <input data-test="company-input" v-model="form.company" required />
        </label>

        <label>
          Role title
          <input data-test="title-input" v-model="form.title" required />
        </label>

        <label>
          Source platform
          <input data-test="source-platform-input" v-model="form.source_platform" required />
        </label>

        <label>
          Location
          <input v-model="form.location" placeholder="London, UK" />
        </label>

        <label>
          Source URL
          <input v-model="form.source_url" placeholder="https://company.com/jobs/123" />
        </label>

        <label>
          Next action
          <input v-model="form.next_action" placeholder="Generate pack" />
        </label>

        <label class="full-width">
          Notes
          <textarea v-model="form.notes" rows="3" placeholder="Why this role matters, blockers, quick thoughts"></textarea>
        </label>

        <label class="full-width">
          Job description
          <textarea v-model="form.job_description" rows="5" placeholder="Paste the job description here if you have it"></textarea>
        </label>

        <button class="primary-button" :disabled="saving" type="submit">
          {{ saving ? 'Saving…' : 'Save job' }}
        </button>
      </form>

      <p v-if="successMessage" class="success-copy">{{ successMessage }}</p>
      <p v-if="errorMessage" class="error-copy">{{ errorMessage }}</p>
    </section>

    <section class="panel-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Saved jobs</p>
          <h2>Inbox</h2>
        </div>
        <span class="count-pill">{{ jobs.length }}</span>
      </div>

      <p v-if="loading" class="muted-copy">Loading saved jobs…</p>
      <p v-else-if="!jobs.length" class="muted-copy">No jobs saved yet. Use the form above to create the first one.</p>

      <ul v-else class="job-list">
        <li v-for="job in jobs" :key="job.id" class="job-row">
          <div>
            <h3>{{ job.title }}</h3>
            <p>{{ job.company }}</p>
            <small v-if="job.location">{{ job.location }}</small>
          </div>
          <span class="job-status">{{ job.application?.status ?? 'Saved' }}</span>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.jobs-view {
  padding: 2rem;
  display: grid;
  gap: 1.5rem;
  color: #eef4ff;
}

.panel-card {
  border: 1px solid #273244;
  border-radius: 24px;
  background: #101827;
  box-shadow: 0 24px 80px rgb(0 0 0 / 24%);
  padding: 1.5rem;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.eyebrow {
  margin: 0 0 0.5rem;
  color: #7dd3fc;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1,
h2,
h3,
p {
  margin-top: 0;
}

.job-form {
  margin-top: 1rem;
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

label {
  display: grid;
  gap: 0.45rem;
  color: #d8e6ff;
  font-weight: 600;
}

input,
textarea {
  width: 100%;
  border: 1px solid #334155;
  border-radius: 14px;
  background: #0f172a;
  color: #eef4ff;
  padding: 0.85rem 1rem;
  font: inherit;
}

.full-width {
  grid-column: 1 / -1;
}

.primary-button {
  width: fit-content;
  border: 0;
  border-radius: 999px;
  background: #2563eb;
  color: white;
  padding: 0.85rem 1.2rem;
  font-weight: 700;
  cursor: pointer;
}

.primary-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.success-copy {
  color: #86efac;
  margin-bottom: 0;
}

.error-copy {
  color: #fca5a5;
  margin-bottom: 0;
}

.muted-copy,
small {
  color: #bfd0e8;
}

.count-pill,
.job-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #172033;
  color: #d8e6ff;
  padding: 0.45rem 0.75rem;
}

.job-list {
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
</style>
