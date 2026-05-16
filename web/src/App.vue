<script setup lang="ts">
import { RouterView } from "vue-router";

import WorkflowShell from "./components/layout/WorkflowShell.vue";
</script>

<template>
  <WorkflowShell>
    <RouterView />
  </WorkflowShell>
</template>
