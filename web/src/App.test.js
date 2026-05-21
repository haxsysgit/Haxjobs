import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'

import App from './App.vue'
import { createHaxjobsRouter } from './router'
import { pinia } from './stores/pinia'
import { useWorkspaceStore } from './stores/workspace'

const demoOptionsPayload = {
  cv_fixtures: [{ id: 'demo-cv.pdf', label: 'Agent Engineer CV' }],
  jd_fixtures: [{ id: 'demo-jd.txt', label: '60x Agent Engineer JD' }],
  default_cv_fixture: 'demo-cv.pdf',
  default_jd_fixture: 'demo-jd.txt',
  modes: ['safe', 'stretch', 'interview', 'ideal'],
}

const baseProfile = {
  version: '0.3.0',
  created_at: '2026-05-18T00:00:00Z',
  updated_at: '2026-05-18T00:00:00Z',
  summary: 'Profile built from 1 CV source and kept local.',
  top_skills: ['Python', 'FastAPI', 'Vue', 'Testing'],
  cv_documents: [
    {
      id: 'cv-main',
      label: 'Main CV.pdf',
      kind: 'cv',
      added_at: '2026-05-18T00:00:00Z',
      summary: 'Backend engineer with Python and Vue delivery experience.',
      skills: ['Python', 'FastAPI', 'Vue'],
    },
  ],
  jd_history: [],
  evidence_library: [
    {
      id: 'fact-1',
      category: 'experience',
      text: 'Built Python APIs and internal tools.',
      source_label: 'Main CV.pdf',
    },
  ],
  survey_responses: [],
}

const reviewPayload = {
  ok: true,
  analysis_engine: 'ai',
  metadata: {
    mode: 'interview',
    source: 'upload',
    cv_label: 'Main CV.pdf',
    jd_label: 'Pasted Job Description',
  },
  fit_summary: {
    score: 78,
    label: 'Strong enough',
    matched_requirements: 4,
    total_requirements: 6,
    summary: 'Profile aligns with the core backend requirements.',
  },
  jd_analysis: {
    role_title: 'Backend Engineer',
    section_titles: ['Role'],
    requirements: [],
    recruiter_concerns: ['Proof of production Vue depth'],
    required_skills: ['Python', 'FastAPI'],
    desirable_skills: ['Vue'],
  },
  candidate_evidence: [],
  evidence_map: [
    {
      requirement_id: 'req-1',
      requirement_text: 'Strong Python fundamentals',
      section: 'Role',
      importance: 'required',
      match_label: 'Strong Match',
      claim_label: 'Confirmed',
      supporting_evidence: ['Built Python APIs'],
      suggested_safe_wording: 'Lead with shipped Python API work.',
      risk_warning: null,
    },
    {
      requirement_id: 'req-2',
      requirement_text: 'Production Vue experience',
      section: 'Role',
      importance: 'required',
      match_label: 'Weak Match',
      claim_label: 'Needs User Confirmation',
      supporting_evidence: ['Shipped a small admin panel'],
      suggested_safe_wording: 'Frame it as adjacent frontend delivery.',
      risk_warning: 'Do not oversell scope.',
    },
  ],
  follow_up_questions: [],
  survey_questions: [
    {
      question_id: 'req-2',
      requirement_id: 'req-2',
      requirement_text: 'Production Vue experience',
      prompt: 'Which option is most true for your Vue experience?',
      helper_text: 'Choose the closest true option first.',
      priority: 'high',
      allow_notes: true,
      choices: [
        {
          id: 'direct-example',
          label: 'I did this directly',
          description: 'I have a real project or work example.',
        },
        {
          id: 'related-example',
          label: 'I did something similar',
          description: 'The experience is close, but not exact.',
        },
      ],
    },
  ],
  recruiter_assessment: {
    shortlist_summary: 'Strong backend signals with one frontend proof gap.',
    priority_requirements: ['Strong Python fundamentals', 'Production Vue experience'],
    concerns: ['Proof of production Vue depth'],
    model_tier: 'gpt-5.4-mini',
  },
  evaluator_assessment: {
    fit_score: 78,
    summary: 'Evaluator found one claim that needs user confirmation.',
    weak_claims: [],
    uncertain_claims: [],
    model_tier: 'gpt-5.4-mini',
  },
  verification_questions: [],
  aspirational_pack: {
    label: 'Aspirational sample (non-submittable until user-confirmed)',
    non_submittable: true,
    tailored_cv_markdown: '# Aspirational CV\n\n## Target Role\nBackend Engineer',
    cover_letter_markdown: '# Aspirational Cover Letter',
    interview_notes_markdown: '# Aspirational Interview Notes',
    model_tier: 'gpt-5.5',
  },
  warnings: [],
  markdown_report: '# Analysis',
}

const generatedPackPayload = {
  metadata: {
    mode: 'interview',
    role_title: 'Backend Engineer',
    source: 'upload',
    aspirational: false,
    follow_up_answer_count: 1,
    unanswered_follow_up_count: 0,
    generated_documents: [
      'tailored_cv_markdown',
      'cover_letter_markdown',
      'interview_notes_markdown',
      'application_pack_json',
    ],
  },
  tailored_cv_markdown: '# Tailored CV Draft\n\nTarget role: Backend Engineer',
  cover_letter_markdown: '# Cover Letter Draft\n\nDear Hiring Team,',
  interview_notes_markdown: '# Application Notes\n\n## Strongest Talking Points',
  evidence_map_json: reviewPayload.evidence_map,
  application_pack_json: {
    documents: {
      tailored_cv_markdown: '# Tailored CV Draft',
    },
  },
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function installFetchMock(overrides = {}) {
  const review = overrides.review ?? reviewPayload
  const generated = overrides.generated ?? generatedPackPayload
  const savedProfile = structuredClone(overrides.profile ?? baseProfile)
  const generateBodies = []
  const endpoints = []

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : input.url
    endpoints.push(url)
    if (url.endsWith('/api/health')) return jsonResponse({ ok: true, llm_configured: false })
    if (url.endsWith('/api/demo-options')) return jsonResponse(demoOptionsPayload)
    if (url.endsWith('/api/profile')) return jsonResponse(savedProfile)
    if (url.endsWith('/api/profile/export')) {
      return jsonResponse({ profile: savedProfile, documents: { 'cv-main': 'Python engineer' } })
    }
    if (url.endsWith('/api/profile/import')) return jsonResponse(savedProfile)
    if (url.endsWith('/api/profile/upload-cvs')) return jsonResponse(savedProfile)
    if (url.endsWith('/api/analyze-saved-cv')) return jsonResponse(review)
    if (url.endsWith('/api/analyze-demo')) {
      return jsonResponse({ ...review, metadata: { ...review.metadata, source: 'demo' } })
    }
    if (url.endsWith('/api/profile/survey-response')) {
      const body = JSON.parse(String(init?.body ?? '{}'))
      savedProfile.survey_responses = [
        {
          question_key: `${body.job_id}:${body.requirement_id}`,
          job_id: body.job_id,
          requirement_id: body.requirement_id,
          requirement_text: body.requirement_text,
          choice_id: body.choice_id,
          choice_label: body.choice_label,
          notes: body.notes,
          updated_at: '2026-05-18T00:00:01Z',
        },
      ]
      return jsonResponse(savedProfile)
    }
    if (url.endsWith('/api/generate-application-pack')) {
      generateBodies.push(JSON.parse(String(init?.body ?? '{}')))
      return jsonResponse(generated)
    }
    throw new Error(`Unexpected request: ${url}`)
  })

  return { endpoints, generateBodies }
}

async function renderApp(path = '/') {
  window.history.replaceState({}, '', path)
  const router = createHaxjobsRouter()
  render(App, {
    global: {
      plugins: [
        pinia,
        router,
        [
          PrimeVue,
          {
            theme: {
              preset: Aura,
              options: { darkModeSelector: '.hax-dark-mode', cssLayer: false },
            },
            ripple: true,
            inputVariant: 'filled',
          },
        ],
      ],
    },
  })
  await router.push(path)
  await router.isReady()
  return { router }
}

function resetStore() {
  window.localStorage.clear()
  useWorkspaceStore(pinia).$reset()
}

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    cleanup()
    resetStore()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('bootstraps health, demo options, and profile for the workspace', async () => {
    const requests = installFetchMock()

    await renderApp('/')

    expect(await screen.findByText('Profile built from 1 CV source and kept local.')).toBeTruthy()
    expect((await screen.findAllByText('Main CV.pdf')).length).toBeGreaterThan(0)
    expect(screen.getByText('Python')).toBeTruthy()
    expect(screen.getByTestId('analyze-saved-button')).toBeTruthy()
    expect(requests.endpoints.some((url) => url.endsWith('/api/health'))).toBe(true)
    expect(requests.endpoints.some((url) => url.endsWith('/api/demo-options'))).toBe(true)
    expect(requests.endpoints.some((url) => url.endsWith('/api/profile'))).toBe(true)
  })

  it('accepts a readable JD file and uses it for the analysis path', async () => {
    installFetchMock()

    await renderApp('/')
    await screen.findAllByText('Main CV.pdf')
    await fireEvent.click(screen.getByText('Add JD another way'))

    const file = new File(['Senior backend role with Python, FastAPI, Vue, and testing.'], 'jd.txt', {
      type: 'text/plain',
    })

    await fireEvent.change(screen.getByLabelText(/Upload JD file/i), {
      target: { files: [file] },
    })

    await waitFor(() => {
      expect(screen.getByTestId('jd-input')).toHaveValue(
        'Senior backend role with Python, FastAPI, Vue, and testing.',
      )
    })
    expect(screen.getByText('9 words ready for analysis')).toBeTruthy()
    expect(screen.getByTestId('analyze-saved-button')).not.toBeDisabled()
  })

  it('runs the demo flow and reaches review', async () => {
    installFetchMock()

    await renderApp('/')
    await screen.findAllByText('Main CV.pdf')
    await fireEvent.click(screen.getByText('Test with fixtures'))
    await fireEvent.click(screen.getByTestId('demo-button'))

    expect(await screen.findByText('Guided review')).toBeTruthy()
    expect(screen.getByText('Add only the details that improve the draft')).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: 'Production Vue experience' }).length).toBeGreaterThan(0)
    expect(screen.getByText('I did this directly')).toBeTruthy()
  })

  it('blocks drafts until required survey answers are selected', async () => {
    installFetchMock()
    const { router } = await renderApp('/')

    await screen.findAllByText('Main CV.pdf')
    await fireEvent.click(screen.getByText('Test with fixtures'))
    await fireEvent.click(screen.getByTestId('demo-button'))
    await screen.findByText('Guided review')

    await router.push('/drafts')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('review')
  })

  it('uses a saved CV, persists a survey answer, and sends confirmations to generation', async () => {
    const requests = installFetchMock()

    await renderApp('/')
    await screen.findAllByText('Main CV.pdf')

    await fireEvent.update(screen.getByTestId('jd-input'), 'Backend engineer role with Python and Vue.')
    await waitFor(() => {
      expect(screen.getByTestId('analyze-saved-button')).not.toBeDisabled()
    })
    await fireEvent.click(screen.getByTestId('analyze-saved-button'))

    expect(await screen.findByText('Add only the details that improve the draft')).toBeTruthy()
    expect(screen.getByText('Keep strong wording believable')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Open Pack' })).toBeDisabled()

    await fireEvent.click(screen.getByRole('button', { name: /I did this directly/i }))
    await fireEvent.click(screen.getByRole('button', { name: /Confirmed/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open Pack' })).not.toBeDisabled()
    })
    await fireEvent.click(screen.getByRole('button', { name: 'Open Pack' }))

    expect(await screen.findByText('Generate recruiter-ready materials')).toBeTruthy()
    expect(screen.getByText('Reference only')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Copy/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Download/i })).toBeTruthy()

    await fireEvent.click(screen.getByRole('button', { name: /Generate Pack/i }))

    expect(await screen.findByTestId('document-rendered')).toBeTruthy()
    expect(screen.getByText('Aspirational sample (non-submittable until user-confirmed)')).toBeTruthy()
    expect(requests.generateBodies).toHaveLength(1)
    expect(requests.generateBodies[0].follow_up_answers).toEqual([
      {
        requirement_id: 'req-2',
        answer: 'I did this directly',
        skipped: false,
      },
    ])
    expect(requests.generateBodies[0].user_claim_confirmations).toEqual([
      {
        requirement_id: 'req-2',
        status: 'confirmed',
        notes: '',
      },
    ])
  })
})
