<script setup>
import { RouterLink, RouterView } from 'vue-router'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/profiles', label: 'Profiles' },
]
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">HaxJobs</RouterLink>
      <nav>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">{{ item.label }}</RouterLink>
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
  gap: 1rem;
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

nav {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

nav a {
  color: #bfd0e8;
  text-decoration: none;
  padding: 0.45rem 0.7rem;
  border-radius: 999px;
}

nav a.router-link-exact-active {
  background: #172033;
  color: #eef4ff;
}
</style>
