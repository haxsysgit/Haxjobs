<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">HaxJobs</RouterLink>
      <nav>
        <RouterLink to="/">Dashboard</RouterLink>
      </nav>
    </header>

    <RouterView />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: #0b1020;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  border-bottom: 1px solid #1f2937;
  background: #0f172a;
}

.brand {
  color: #eef4ff;
  font-size: 1.2rem;
  font-weight: 800;
  text-decoration: none;
}

nav a {
  color: #bfd0e8;
  text-decoration: none;
}
</style>
