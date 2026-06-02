const API_BASE_URL = import.meta.env.VITE_HAXJOBS_API_URL ?? 'http://localhost:8000'

export async function fetchHealthStatus() {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(`Health check failed with ${response.status}`)
  }

  return response.json()
}
