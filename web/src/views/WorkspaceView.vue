<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { ArrowRight, ClipboardPaste, FileText, Link, Play, RotateCcw, SlidersHorizontal } from '@lucide/vue'

import ProfileConsole from '../components/ProfileConsole.vue'
import { useWorkspaceStore } from '../stores/workspace'

const router = useRouter()
const workspace = useWorkspaceStore()
const uploadFile = ref(null)
const jdFileName = ref('')
const jdUrl = ref('')
const jdImportError = ref('')
const jdImporting = ref(false)

const modeOptions = [
  { label: 'Safe', value: 'safe' },
  { label: 'Stretch', value: 'stretch' },
  { label: 'Interview', value: 'interview' },
  { label: 'Ideal sample', value: 'ideal' },
]

const demoCvOptions = computed(() =>
  (workspace.demoOptions?.cv_fixtures ?? []).map((item) => ({ label: item.label, value: item.id })),
)
const demoJdOptions = computed(() =>
  (workspace.demoOptions?.jd_fixtures ?? []).map((item) => ({ label: item.label, value: item.id })),
)
const canAnalyzeSaved = computed(() => Boolean(workspace.activeCvDocumentId && workspace.jdText.trim()))
const canAnalyzeUpload = computed(() => Boolean(uploadFile.value && workspace.jdText.trim()))
const jdWordCount = computed(() => workspace.jdText.trim().split(/\s+/).filter(Boolean).length)
const selectedDemoLabel = computed(() => {
  const jd = demoJdOptions.value.find((item) => item.value === workspace.demoJdFixture)?.label
  return jd ? `Try demo: ${jd}` : 'Try demo'
})

async function analyzeSaved() {
  await workspace.runSavedCvAnalysis()
  if (workspace.analysis) router.push('/review')
}

async function analyzeUpload() {
  await workspace.runUploadAnalysis(uploadFile.value)
  if (workspace.analysis) router.push('/review')
}

async function analyzeDemo() {
  await workspace.runDemoAnalysis()
  if (workspace.analysis) router.push('/review')
}

function handleUpload(event) {
  uploadFile.value = event.target.files?.[0] ?? null
}

async function handleJdFile(event) {
  const file = event.target.files?.[0]
  jdImportError.value = ''
  if (!file) return

  const supported =
    file.type.startsWith('text/') ||
    /\.(txt|md|markdown|rtf|csv)$/i.test(file.name)

  if (!supported) {
    jdImportError.value = 'For now, upload a text, Markdown, RTF, or CSV job description.'
    event.target.value = ''
    return
  }

  workspace.jdText = await file.text()
  jdFileName.value = file.name
  workspace.remember()
  event.target.value = ''
}

async function importJdUrl() {
  const url = jdUrl.value.trim()
  jdImportError.value = ''
  if (!url) return

  jdImporting.value = true
  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error('Could not read that URL.')
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType && !contentType.includes('text') && !contentType.includes('json')) {
      throw new Error('That URL did not return readable text.')
    }
    workspace.jdText = await response.text()
    workspace.remember()
  } catch (error) {
    jdImportError.value =
      error instanceof Error
        ? `${error.message} Paste the JD text if the job board blocks browser access.`
        : 'Paste the JD text if the job board blocks browser access.'
  } finally {
    jdImporting.value = false
  }
}
</script>

<template>
  <div class="workspace-single">
    <section class="workspace-panel primary-workspace">
      <div class="panel-heading">
        <div>
          <p class="context-kicker">Main workflow</p>
          <h2>Paste a JD. Generate the pack.</h2>
          <p>Use your saved profile, review only the important checks, then export the CV, cover letter, and notes.</p>
        </div>
        <Button text rounded severity="secondary" aria-label="Clear session" title="Clear session" @click="workspace.clearSession()">
          <RotateCcw :size="18" />
        </Button>
      </div>

      <ProfileConsole />

      <div class="flow-strip" aria-label="Application flow">
        <span><ClipboardPaste :size="16" /> Add JD</span>
        <span><ArrowRight :size="14" /> Review matches</span>
        <span><FileText :size="16" /> Generate pack</span>
      </div>

      <label class="field-label" for="jd-input">Job description</label>
      <Textarea
        id="jd-input"
        v-model="workspace.jdText"
        data-testid="jd-input"
        rows="13"
        class="full-control jd-editor"
        placeholder="Paste the job description here."
        @blur="workspace.remember()"
      />
      <p class="input-meter">{{ jdWordCount }} words ready for analysis</p>

      <div class="action-strip">
        <Button
          data-testid="analyze-saved-button"
          :disabled="!canAnalyzeSaved || workspace.loading"
          @click="analyzeSaved"
        >
          <ArrowRight :size="17" />
          Analyze saved CV
        </Button>
      </div>

      <details class="workspace-disclosure">
        <summary>
          <FileText :size="17" aria-hidden="true" />
          Add JD another way
        </summary>
        <div class="jd-import-grid">
          <label class="import-tile" for="jd-file">
            <FileText :size="18" aria-hidden="true" />
            <span>
              <strong>Upload JD file</strong>
              <small>{{ jdFileName || 'TXT, MD, RTF, CSV' }}</small>
            </span>
            <input id="jd-file" class="sr-only" type="file" accept=".txt,.md,.markdown,.rtf,.csv,text/*" @change="handleJdFile" />
          </label>

          <div class="import-tile url-import">
            <Link :size="18" aria-hidden="true" />
            <span>
              <strong>Import URL</strong>
              <small>Some job boards block this</small>
            </span>
            <div class="url-row">
              <InputText v-model="jdUrl" aria-label="Job description URL" placeholder="https://..." />
              <Button severity="secondary" :disabled="jdImporting || !jdUrl.trim()" @click="importJdUrl">
                Import
              </Button>
            </div>
          </div>
        </div>
        <p v-if="jdImportError" class="inline-error">{{ jdImportError }}</p>
      </details>

      <details class="workspace-disclosure">
        <summary>
          <SlidersHorizontal :size="17" aria-hidden="true" />
          Advanced options
        </summary>
        <div class="advanced-grid">
          <div>
            <label class="field-label" for="mode-select">Mode</label>
            <Select
              id="mode-select"
              v-model="workspace.selectedMode"
              :options="modeOptions"
              option-label="label"
              option-value="value"
              class="full-control compact-control"
              @change="workspace.remember()"
            />
          </div>
          <div>
            <label class="field-label" for="cv-upload">One-off CV upload</label>
            <input id="cv-upload" class="file-input compact-file" type="file" @change="handleUpload" />
          </div>
        </div>
        <Button
          severity="secondary"
          :disabled="!canAnalyzeUpload || workspace.loading"
          @click="analyzeUpload"
        >
          Analyze uploaded CV
        </Button>
      </details>

      <details class="workspace-disclosure">
        <summary>
          <Play :size="17" aria-hidden="true" />
          Test with fixtures
        </summary>
        <Button data-testid="demo-button" severity="secondary" :disabled="workspace.loading" @click="analyzeDemo">
          <Play :size="17" />
          {{ selectedDemoLabel }}
        </Button>
      </details>
    </section>
  </div>
</template>
