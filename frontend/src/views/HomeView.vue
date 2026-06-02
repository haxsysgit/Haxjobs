<script setup>
import { onMounted, ref } from 'vue'

import { fetchHealthStatus } from '@/services/api'

const healthStatus = ref('checking')
const healthMessage = ref('Checking backend connection…')

onMounted(async () => {
  try {
    const health = await fetchHealthStatus()
    healthStatus.value = health.status
    healthMessage.value = `${health.service} is online`
  } catch (error) {
    healthStatus.value = 'offline'
    healthMessage.value = 'Backend is not reachable yet'
    console.error(error)
  }
})
</script>

<template>
  <main class="home-view">
    <section class="hero-card">
      <p class="eyebrow">HaxJobs 0.1.x</p>
      <h1>Hermes-powered job search starts here.</h1>
      <p class="summary">
        HaxJobs is the UI and workflow layer for the Hermes job application pipeline. This first slice wires the local app shell to the API.
      </p>

      <div class="health-pill" :data-status="healthStatus">
        {{ healthMessage }}
      </div>
    </section>
  </main>
</template>

<style scoped>
.home-view {
  min-height: 70vh;
  display: grid;
  place-items: center;
  padding: 2rem;
}

.hero-card {
  max-width: 720px;
  padding: 2rem;
  border: 1px solid #273244;
  border-radius: 24px;
  background: #101827;
  color: #eef4ff;
  box-shadow: 0 24px 80px rgb(0 0 0 / 24%);
}

.eyebrow {
  margin: 0 0 0.75rem;
  color: #7dd3fc;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1;
}

.summary {
  margin: 1rem 0 1.5rem;
  color: #bfd0e8;
  font-size: 1.05rem;
}

.health-pill {
  display: inline-flex;
  padding: 0.7rem 1rem;
  border-radius: 999px;
  background: #172033;
  color: #d8e6ff;
  font-weight: 700;
}

.health-pill[data-status='ok'] {
  background: #064e3b;
  color: #d1fae5;
}

.health-pill[data-status='offline'] {
  background: #7f1d1d;
  color: #fee2e2;
}
</style>
