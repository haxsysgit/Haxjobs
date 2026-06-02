<script setup>
import { onMounted, ref } from 'vue'

import { fetchProfiles } from '@/services/api'

const profiles = ref([])
const loading = ref(true)
const errorMessage = ref('')

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
  <main class="profiles-view">
    <section class="panel-card">
      <p class="eyebrow">Profile workspace</p>
      <h1>Stored profiles and reusable truth</h1>
      <p class="summary">
        This is where HaxJobs starts becoming Hermes’s truth surface. Right now you can inspect stored profiles here, and private local seed data still lives in
        <code>data/private/arinze_profile.local.json</code>.
      </p>
      <p class="import-note">
        Private import path: <code>data/private/arinze_profile.local.json</code>
      </p>
    </section>

    <section class="panel-card">
      <div class="panel-heading">
        <h2>Profiles</h2>
        <span class="count-pill">{{ profiles.length }}</span>
      </div>

      <p v-if="loading" class="muted-copy">Loading profiles…</p>
      <p v-else-if="errorMessage" class="error-copy">{{ errorMessage }}</p>
      <p v-else-if="!profiles.length" class="muted-copy">No profiles stored yet. Import the private local fixture or create one through the API.</p>

      <ul v-else class="profile-list">
        <li v-for="profile in profiles" :key="profile.id" class="profile-row">
          <div>
            <h3>{{ profile.full_name }}</h3>
            <p>{{ profile.preferred_roles?.join(', ') || 'No preferred roles saved yet' }}</p>
          </div>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.profiles-view {
  padding: 2rem;
  display: grid;
  gap: 1.5rem;
  color: #eef4ff;
}

.panel-card {
  border: 1px solid #273244;
  border-radius: 24px;
  background: #101827;
  box-shadow: 0 24px 80px rgb(0 0 0 / 24%);
  padding: 1.5rem;
}

.eyebrow {
  margin: 0 0 0.5rem;
  color: #7dd3fc;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary,
.import-note,
.muted-copy,
.profile-row p {
  color: #bfd0e8;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.count-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #172033;
  color: #d8e6ff;
  padding: 0.45rem 0.75rem;
}

.profile-list {
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
}

.profile-row {
  padding: 1rem 0;
  border-top: 1px solid #1f2937;
}

.profile-row:first-child {
  border-top: 0;
  padding-top: 0;
}

.profile-row h3,
.profile-row p {
  margin: 0;
}

.profile-row p {
  margin-top: 0.35rem;
}

.error-copy {
  color: #fca5a5;
}

code {
  color: #fde68a;
}
</style>
