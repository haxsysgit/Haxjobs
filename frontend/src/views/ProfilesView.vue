<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchProfiles } from '@/services/api'

const profiles = ref([])
const loading = ref(true)
const errorMessage = ref('')

const truthLayers = [
  { label: 'Facts', detail: 'stable profile truth', glow: 'cyan' },
  { label: 'Answers', detail: 'reusable application responses', glow: 'violet' },
  { label: 'Approvals', detail: 'human gates before risky actions', glow: 'green' },
]

const profileScore = computed(() => Math.min(100, 22 + profiles.value.length * 38))

onMounted(async () => {
  try {
    profiles.value = await fetchProfiles()
  } catch (error) {
    errorMessage.value = 'Could not load stored profiles yet.'
    console.error(error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="profiles-view shell-page">
    <section class="profile-hero hax-card">
      <div>
        <p class="eyebrow">Truth surface</p>
        <h1><span class="gradient-text">Profile memory</span> Hermes can trust.</h1>
        <p class="summary">
          This is where HaxJobs stores the stable facts and reusable answers that stop every application from becoming a fresh interrogation.
        </p>
      </div>

      <div class="truth-score" :style="{ '--meter': `${profileScore}%` }">
        <span>{{ profileScore }}%</span>
        <small>profile base</small>
      </div>
    </section>

    <section class="truth-grid">
      <article v-for="layer in truthLayers" :key="layer.label" class="truth-card hax-card" :data-glow="layer.glow">
        <span class="truth-icon">{{ layer.label.slice(0, 1) }}</span>
        <h2>{{ layer.label }}</h2>
        <p>{{ layer.detail }}</p>
      </article>
    </section>

    <section class="profiles-panel hax-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Stored profiles</p>
          <h2>Reusable application identity</h2>
        </div>
        <span class="pill">{{ profiles.length }}</span>
      </div>

      <div class="import-callout">
        <span>Private seed</span>
        <code>data/private/arinze_profile.local.json</code>
      </div>

      <p v-if="loading" class="muted-copy">Loading profiles…</p>
      <p v-else-if="errorMessage" class="error-copy">{{ errorMessage }}</p>
      <p v-else-if="!profiles.length" class="muted-copy">No profiles stored yet. Import the private local fixture or create one through the API.</p>

      <ul v-else class="profile-list">
        <li v-for="profile in profiles" :key="profile.id" class="profile-row">
          <span class="profile-avatar">{{ profile.full_name?.slice(0, 2).toUpperCase() || 'HX' }}</span>
          <div>
            <h3>{{ profile.full_name }}</h3>
            <p>{{ profile.preferred_roles?.join(', ') || 'No preferred roles saved yet' }}</p>
          </div>
          <span class="profile-pill">ready</span>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.profiles-view {
  display: grid;
  gap: 1.2rem;
  padding-bottom: 8rem;
}

.profile-hero {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 2rem;
  padding: clamp(1.4rem, 4vw, 2.6rem);
}

.profile-hero h1 {
  margin: 0;
  max-width: 12ch;
  font-size: clamp(2.8rem, 7vw, 5.8rem);
  line-height: 0.9;
  letter-spacing: -0.07em;
}

.summary {
  max-width: 66ch;
  color: var(--text-soft);
  line-height: 1.7;
}

.truth-score {
  width: 10rem;
  height: 10rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, var(--bg) 0 55%, transparent 56%),
    conic-gradient(var(--accent) var(--meter), var(--surface-soft) 0);
  box-shadow: var(--glow);
}

.truth-score span,
.truth-score small {
  grid-area: 1 / 1;
}

.truth-score span {
  transform: translateY(-0.45rem);
  font-size: 2rem;
  font-weight: 900;
}

.truth-score small {
  transform: translateY(1.2rem);
  color: var(--muted);
}

.truth-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.2rem;
}

.truth-card,
.profiles-panel {
  padding: 1.25rem;
}

.truth-card {
  min-height: 190px;
  display: grid;
  align-content: space-between;
  transition: transform 180ms ease, background 180ms ease;
}

.truth-card:hover {
  transform: translateY(-5px) rotate(-0.5deg);
  background: var(--surface-strong);
}

.truth-icon {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: white;
  font-family: var(--font-mono);
  font-weight: 900;
}

.truth-card h2,
.truth-card p {
  margin: 0;
}

.truth-card p {
  color: var(--text-soft);
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.panel-heading h2 {
  margin: 0;
  font-size: clamp(1.5rem, 3vw, 2.4rem);
  letter-spacing: -0.05em;
}

.import-callout {
  display: flex;
  gap: 0.7rem;
  flex-wrap: wrap;
  align-items: center;
  width: fit-content;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--text-soft);
  padding: 0.7rem 0.85rem;
  margin: 1.2rem 0;
}

.import-callout span {
  color: var(--accent-2);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

code {
  color: var(--warning);
}

.profile-list {
  display: grid;
  gap: 0.75rem;
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
}

.profile-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.85rem;
  align-items: center;
  border: 1px solid var(--border-soft);
  border-radius: 22px;
  background: var(--surface-soft);
  padding: 0.95rem;
}

.profile-avatar {
  display: grid;
  place-items: center;
  width: 2.8rem;
  height: 2.8rem;
  border-radius: 17px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: white;
  font-family: var(--font-mono);
  font-weight: 900;
}

.profile-row h3,
.profile-row p {
  margin: 0;
}

.profile-row p,
.muted-copy {
  color: var(--text-soft);
}

.profile-pill {
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--accent-3);
  padding: 0.45rem 0.7rem;
}

.error-copy {
  color: var(--danger);
}

@media (max-width: 920px) {
  .profile-hero,
  .truth-grid {
    grid-template-columns: 1fr;
  }
}
</style>
