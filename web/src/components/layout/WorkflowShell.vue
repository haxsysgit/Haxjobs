<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { canAccessOutputs, hasAnalysis } from "../../state/app-state";

const route = useRoute();

interface NavItem {
  label: string;
  to: string;
  enabled: boolean;
}

interface SectionLink {
  id: string;
  label: string;
}

const navItems = computed<NavItem[]>(() => [
  {
    label: "Workspace",
    to: "/",
    enabled: true
  },
  {
    label: "Review",
    to: "/review",
    enabled: hasAnalysis()
  },
  {
    label: "Drafts",
    to: "/drafts",
    enabled: canAccessOutputs()
  }
]);

const sectionLinks = computed<SectionLink[]>(() => {
  if (route.name === "review") {
    return [
      { id: "evidence", label: "Evidence" },
      { id: "questions", label: "Questions" }
    ];
  }
  if (route.name === "drafts") {
    return [{ id: "documents", label: "Documents" }];
  }
  return [
    { id: "intake", label: "Intake" },
    { id: "advanced", label: "Advanced" },
    { id: "demo", label: "Demo" }
  ];
});
</script>

<template>
  <main class="app-layout">
    <aside class="app-sidebar">
      <header class="sidebar-brand">
        <div class="brand-mark">H</div>
        <div>
          <p class="sidebar-eyebrow">HaxJobs</p>
          <h1>Workflow</h1>
        </div>
      </header>

      <nav class="sidebar-nav" aria-label="Primary workflow navigation">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.enabled ? item.to : route.fullPath"
          class="sidebar-link"
          :class="{ active: route.path === item.to, disabled: !item.enabled }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <section class="sidebar-sections" aria-label="Current page sections">
        <p class="sidebar-eyebrow">Sections</p>
        <a v-for="item in sectionLinks" :key="item.id" class="section-link" :href="`#${item.id}`">
          {{ item.label }}
        </a>
      </section>
    </aside>

    <section class="app-content">
      <slot />
    </section>
  </main>
</template>
