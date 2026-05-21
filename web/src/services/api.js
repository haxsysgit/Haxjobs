export class ApiError extends Error {
  constructor(message, kind) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
  }
}

export function getApiBaseUrl() {
  return (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '')
}

export function buildApiUrl(path) {
  const base = getApiBaseUrl()
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

async function requestJson(path, init) {
  let response
  try {
    response = await fetch(buildApiUrl(path), init)
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError(
        'Backend unavailable. Start `./scripts/dev.sh start` and try again.',
        'backend_unavailable',
      )
    }
    throw error
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(payload?.detail ?? 'Request failed.', 'request_failed')
  }

  return response.json()
}

export function getHealth() {
  return requestJson('/api/health')
}

export function getDemoOptions() {
  return requestJson('/api/demo-options')
}

export function getProfile() {
  return requestJson('/api/profile')
}

export function exportProfileBundle() {
  return requestJson('/api/profile/export')
}

export function importProfileBundle(bundle) {
  return requestJson('/api/profile/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bundle),
  })
}

export function uploadProfileCvs(files) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('cv_files', file)
  }
  return requestJson('/api/profile/upload-cvs', {
    method: 'POST',
    body: formData,
  })
}

export function saveSurveyResponse(jobId, response) {
  return requestJson('/api/profile/survey-response', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id: jobId,
      requirement_id: response.requirement_id,
      requirement_text: response.requirement_text,
      choice_id: response.choice_id,
      choice_label: response.choice_label,
      notes: response.notes,
    }),
  })
}

export function analyzeCv(file, jdText, mode) {
  const formData = new FormData()
  formData.append('cv_file', file)
  formData.append('jd_text', jdText)
  formData.append('mode', mode)
  return requestJson('/api/analyze', {
    method: 'POST',
    body: formData,
  })
}

export function analyzeSavedCv(cvDocumentId, jdText, mode) {
  return requestJson('/api/analyze-saved-cv', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cv_document_id: cvDocumentId,
      jd_text: jdText,
      mode,
    }),
  })
}

export function analyzeDemo(cvFixture, jdFixture, mode) {
  return requestJson('/api/analyze-demo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cv_fixture: cvFixture,
      jd_fixture: jdFixture,
      mode,
    }),
  })
}

export function generateApplicationPack(payload) {
  return requestJson('/api/generate-application-pack', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
