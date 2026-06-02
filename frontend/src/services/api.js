const API_BASE_URL = import.meta.env.VITE_HAXJOBS_API_URL ?? 'http://localhost:8000'

async function fetchJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`)

  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`)
  }

  return response.json()
}

export async function fetchHealthStatus() {
  return fetchJson('/health')
}

export async function fetchJobs() {
  return fetchJson('/api/jobs')
}

export async function fetchProfiles() {
  return fetchJson('/api/profiles')
}

export async function fetchHermesTasks() {
  return fetchJson('/api/hermes-tasks')
}
