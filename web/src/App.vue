<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import WorkflowShell from './layouts/WorkflowShell.vue'
import { useWorkspaceStore } from './stores/workspace'

const workspace = useWorkspaceStore()

onMounted(() => {
  workspace.bootstrap()
})
</script>

<template>
  <WorkflowShell>
    <RouterView />
  </WorkflowShell>
</template>
