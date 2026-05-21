<script setup>
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Select from 'primevue/select'
import { Download, FileUp, Upload, UserRound } from '@lucide/vue'

import { useWorkspaceStore } from '../stores/workspace'

const workspace = useWorkspaceStore()
const cvInput = ref(null)
const importInput = ref(null)

const cvOptions = computed(() =>
  (workspace.profile?.cv_documents ?? []).map((document) => ({
    label: document.label,
    value: document.id,
  })),
)

async function handleCvUpload(event) {
  const files = Array.from(event.target.files ?? [])
  if (files.length) await workspace.importCvs(files)
  event.target.value = ''
}

async function handleBundleImport(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const bundle = JSON.parse(await file.text())
  await workspace.importProfile(bundle)
  event.target.value = ''
}

async function downloadProfile() {
  const bundle = await workspace.exportProfile()
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'haxjobs-profile.json'
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <section class="profile-console" aria-label="Profile source">
    <div class="console-head">
      <UserRound :size="20" aria-hidden="true" />
      <div>
        <h2>Candidate profile</h2>
        <p>{{ workspace.profile?.summary ?? workspace.healthDetail }}</p>
      </div>
    </div>

    <input ref="cvInput" class="sr-only" type="file" multiple @change="handleCvUpload" />
    <input ref="importInput" class="sr-only" type="file" accept="application/json" @change="handleBundleImport" />

    <div class="profile-row">
      <div>
        <label class="field-label" for="cv-select">CV used for matching</label>
        <Select
          id="cv-select"
          v-model="workspace.activeCvDocumentId"
          :options="cvOptions"
          option-label="label"
          option-value="value"
          class="full-control"
          placeholder="Choose a saved CV"
          @change="workspace.remember()"
        />
      </div>
      <Button severity="secondary" @click="cvInput?.click()">
        <Upload :size="17" />
        Upload CV
      </Button>
    </div>

    <div v-if="workspace.profile?.top_skills?.length" class="tag-row compact-tags">
      <span v-for="skill in workspace.profile.top_skills.slice(0, 8)" :key="skill">{{ skill }}</span>
    </div>

    <details class="profile-tools">
      <summary>Profile tools</summary>
      <div class="action-strip">
        <Button severity="secondary" size="small" @click="importInput?.click()">
          <FileUp :size="16" />
          Import
        </Button>
        <Button severity="secondary" size="small" @click="downloadProfile">
          <Download :size="16" />
          Export
        </Button>
      </div>
    </details>
  </section>
</template>
