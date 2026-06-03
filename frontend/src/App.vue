<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

const navItems = [
  { to: '/', label: 'Dashboard', glyph: '✦' },
  { to: '/jobs', label: 'Jobs', glyph: '⌁' },
  { to: '/profiles', label: 'Profiles', glyph: '◈' },
]

const commandDockItems = [
  { label: 'Analyze', hint: '0.2.0', tone: 'cyan' },
  { label: 'Pack', hint: '0.2.x', tone: 'violet' },
  { label: 'Outreach', hint: '0.3.x', tone: 'green' },
  { label: 'Apply assist', hint: 'later', tone: 'amber' },
]

const theme = ref('dark')
const themeLabel = computed(() => (theme.value === 'dark' ? 'Dark cockpit' : 'Light cockpit'))

function applyTheme(nextTheme) {
  theme.value = nextTheme
  document.documentElement.dataset.theme = nextTheme
  localStorage.setItem('haxjobs-theme', nextTheme)
}

function toggleTheme() {
  applyTheme(theme.value === 'dark' ? 'light' : 'dark')
}

onMounted(() => {
  const savedTheme = localStorage.getItem('haxjobs-theme')
  applyTheme(savedTheme === 'light' ? 'light' : 'dark')
})
</script>

<template>
  <div class="app-shell">
    <div class="ambient-orb orb-one"></div>
    <div class="ambient-orb orb-two"></div>

    <header class="topbar shell-page">
      <RouterLink class="brand" to="/" aria-label="HaxJobs dashboard">
        <span class="brand-mark">HX</span>
        <span>
          <strong>HaxJobs</strong>
          <small>Hermes cockpit</small>
        </span>
      </RouterLink>

      <nav aria-label="Main navigation">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
          <span>{{ item.glyph }}</span>
          {{ item.label }}
        </RouterLink>
      </nav>

      <button data-test="theme-toggle" class="theme-toggle" type="button" @click="toggleTheme">
        <span class="toggle-orbit" aria-hidden="true"></span>
        {{ themeLabel }}
      </button>
    </header>

    <aside class="command-dock shell-page" aria-label="Future Hermes command dock">
      <p>Command Dock</p>
      <div class="dock-items">
        <button v-for="item in commandDockItems" :key="item.label" class="dock-item" :data-tone="item.tone" type="button">
          <span>{{ item.label }}</span>
          <small>{{ item.hint }}</small>
        </button>
      </div>
    </aside>

    <RouterView />
  </div>
</template>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  isolation: isolate;
}

.ambient-orb {
  position: fixed;
  z-index: 0;
  width: 28rem;
  height: 28rem;
  border-radius: 999px;
  filter: blur(28px);
  opacity: 0.34;
  pointer-events: none;
  animation: floaty 8s ease-in-out infinite;
}

.orb-one {
  top: -10rem;
  left: -8rem;
  background: radial-gradient(circle, var(--accent), transparent 65%);
}

.orb-two {
  right: -8rem;
  bottom: 8rem;
  background: radial-gradient(circle, var(--accent-2), transparent 65%);
  animation-delay: -3s;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  padding-bottom: 1rem;
  backdrop-filter: blur(24px);
}

.topbar::after {
  content: '';
  position: absolute;
  left: 1.25rem;
  right: 1.25rem;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border), transparent);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.8rem;
  color: var(--text);
  text-decoration: none;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 2.65rem;
  height: 2.65rem;
  border: 1px solid var(--border);
  border-radius: 16px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent) 70%, transparent), color-mix(in srgb, var(--accent-2) 64%, transparent)),
    var(--surface);
  box-shadow: var(--glow);
  color: white;
  font-family: var(--font-mono);
  font-weight: 800;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 1rem;
  line-height: 1.1;
}

.brand small {
  color: var(--muted);
  font-size: 0.72rem;
  margin-top: 0.18rem;
}

nav {
  justify-self: center;
  display: flex;
  gap: 0.5rem;
  padding: 0.35rem;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: var(--glass);
  box-shadow: inset 0 0 0 1px rgb(255 255 255 / 3%);
}

nav a {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--text-soft);
  text-decoration: none;
  padding: 0.65rem 0.85rem;
  border-radius: 999px;
  font-size: 0.92rem;
  transition: background 180ms ease, color 180ms ease, transform 180ms ease;
}

nav a:hover {
  color: var(--text);
  transform: translateY(-1px);
}

nav a.router-link-exact-active {
  background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 28%, transparent), color-mix(in srgb, var(--accent-2) 16%, transparent));
  color: var(--text);
  box-shadow: inset 0 0 0 1px var(--border);
}

.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--glass);
  color: var(--text-soft);
  padding: 0.58rem 0.75rem;
  cursor: pointer;
}

.toggle-orbit {
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 999px;
  background: radial-gradient(circle at 30% 30%, white, var(--accent-2) 28%, var(--accent) 62%, transparent 64%);
  box-shadow: 0 0 22px color-mix(in srgb, var(--accent) 60%, transparent);
}

.command-dock {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 0.85rem;
  margin-top: -0.2rem;
  margin-bottom: 0.75rem;
}

.command-dock::before {
  content: '';
  position: absolute;
  inset: 1.25rem;
  z-index: -1;
  border: 1px solid var(--border);
  border-radius: 24px;
  background: var(--glass);
  box-shadow: var(--shadow);
  backdrop-filter: blur(24px);
}

.command-dock p {
  margin: 0 0 0.55rem;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.dock-items {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}

.dock-item {
  display: grid;
  gap: 0.2rem;
  border: 1px solid var(--border-soft);
  border-radius: 16px;
  background: var(--surface-soft);
  color: var(--text);
  padding: 0.65rem 0.75rem;
  text-align: left;
  cursor: pointer;
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
}

.dock-item:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--accent-2) 48%, var(--border));
  background: var(--surface-strong);
}

.dock-item small {
  color: var(--muted);
  font-family: var(--font-mono);
}

@media (max-width: 860px) {
  .topbar {
    grid-template-columns: 1fr;
  }

  nav {
    justify-self: stretch;
    overflow-x: auto;
  }

  .theme-toggle {
    width: fit-content;
  }

  .dock-items {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
