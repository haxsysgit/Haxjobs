<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { BriefcaseBusiness, ClipboardCheck, FileText, LibraryBig, RadioTower, ShieldCheck } from '@lucide/vue'

import { useWorkspaceStore } from '../stores/workspace'

const route = useRoute()
const workspace = useWorkspaceStore()

const navItems = [
  { name: 'workspace', label: 'Workspace', to: '/', icon: LibraryBig },
  { name: 'review', label: 'Review', to: '/review', icon: ClipboardCheck },
  { name: 'drafts', label: 'Drafts', to: '/drafts', icon: FileText },
]

const statusClass = computed(() => `shell-status is-${workspace.healthState}`)
const roleTitle = computed(() => workspace.analysis?.jd_analysis?.role_title ?? 'No active role')
const contextLine = computed(() => {
  if (!workspace.analysis) return 'Profile setup console'
  return `${workspace.analysis.metadata.cv_label} / ${workspace.analysis.metadata.mode}`
})
</script>

<template>
  <div class="workflow-shell">
    <aside class="shell-sidebar" aria-label="Workflow navigation">
      <div class="brand-block">
        <div class="brand-mark">
          <BriefcaseBusiness :size="20" aria-hidden="true" />
        </div>
        <div>
          <p class="brand-name">HaxJobs</p>
          <p class="brand-caption">tailored packs</p>
        </div>
      </div>

      <nav class="shell-nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="item.to"
          class="shell-nav-item"
          :class="{ active: route.name === item.name }"
        >
          <component :is="item.icon" :size="18" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="shell-safety">
        <ShieldCheck :size="18" aria-hidden="true" />
        <span>Best truthful impression first.</span>
      </div>
    </aside>

    <section class="shell-main">
      <header class="shell-topbar">
        <div>
          <p class="context-kicker">Current application</p>
          <h1>{{ roleTitle }}</h1>
          <p>{{ contextLine }}</p>
        </div>
        <div :class="statusClass" role="status">
          <RadioTower :size="17" aria-hidden="true" />
          <span>{{ workspace.healthMessage }}</span>
        </div>
      </header>

      <main class="shell-content">
        <slot />
      </main>
    </section>
  </div>
</template>
