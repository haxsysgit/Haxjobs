<script setup>
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import { Copy, Download, RefreshCw } from '@lucide/vue'

import MarkdownDocument from '../components/MarkdownDocument.vue'
import { useWorkspaceStore } from '../stores/workspace'

const workspace = useWorkspaceStore()
const activeDocument = ref('cv')

const documents = computed(() => [
  {
    key: 'cv',
    label: 'Tailored CV',
    markdown: workspace.generatedPack?.tailored_cv_markdown ?? '',
    filename: 'tailored_cv.md',
  },
  {
    key: 'letter',
    label: 'Cover letter',
    markdown: workspace.generatedPack?.cover_letter_markdown ?? '',
    filename: 'cover_letter.md',
  },
  {
    key: 'notes',
    label: 'Application notes',
    markdown: workspace.generatedPack?.interview_notes_markdown ?? '',
    filename: 'application_notes.md',
  },
])

const activeMarkdown = computed(
  () => documents.value.find((document) => document.key === activeDocument.value)?.markdown ?? '',
)

async function generate() {
  await workspace.runGeneration()
}

async function copyDocument() {
  await navigator.clipboard?.writeText(activeMarkdown.value)
}

function downloadDocument() {
  const current = documents.value.find((item) => item.key === activeDocument.value)
  if (!current) return
  const blob = new Blob([current.markdown], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = current.filename
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="drafts-layout">
    <section class="draft-command">
      <div>
        <p class="context-kicker">Drafts</p>
        <h2>Generate recruiter-ready materials</h2>
        <p>Survey answers become follow-up evidence; claim confirmations stay in the generation payload.</p>
      </div>
      <div class="action-strip">
        <Button :disabled="workspace.loading" @click="generate">
          <RefreshCw :size="17" />
          Generate Pack
        </Button>
        <Button severity="secondary" :disabled="!activeMarkdown" @click="copyDocument">
          <Copy :size="17" />
          Copy
        </Button>
        <Button severity="secondary" :disabled="!activeMarkdown" @click="downloadDocument">
          <Download :size="17" />
          Download
        </Button>
      </div>
    </section>

    <section class="draft-workbench">
      <Tabs v-model:value="activeDocument">
        <TabList>
          <Tab v-for="document in documents" :key="document.key" :value="document.key">
            {{ document.label }}
          </Tab>
        </TabList>
        <TabPanels>
          <TabPanel v-for="document in documents" :key="document.key" :value="document.key">
            <MarkdownDocument
              v-if="document.markdown"
              :markdown="document.markdown"
            />
            <div v-else class="empty-document">
              Generate the application pack to fill this document surface.
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </section>

    <aside class="draft-side">
      <section>
        <h3>Optional notes</h3>
        <Textarea
          v-model="workspace.userNotes"
          rows="5"
          class="full-control"
          placeholder="Anything the generator should know, without inventing facts."
          @blur="workspace.remember()"
        />
      </section>

      <section v-if="workspace.analysis?.aspirational_pack" class="reference-panel">
        <p class="context-kicker">Reference only</p>
        <h3>{{ workspace.analysis.aspirational_pack.label }}</h3>
        <p>This sample is separated from the submittable documents and remains non-submittable.</p>
        <MarkdownDocument :markdown="workspace.analysis.aspirational_pack.tailored_cv_markdown" />
      </section>
    </aside>
  </div>
</template>
