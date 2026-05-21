import { defineStore } from 'pinia'

import {
  analyzeCv,
  analyzeDemo,
  analyzeSavedCv,
  exportProfileBundle,
  generateApplicationPack,
  getDemoOptions,
  getHealth,
  getProfile,
  importProfileBundle,
  saveSurveyResponse,
  uploadProfileCvs,
} from '../services/api'

export const STORAGE_KEY = 'haxjobs.workspace.v0.4'

function loadPersistedState() {
  if (typeof window === 'undefined') return {}
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) return {}
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

function persistState(state) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      selectedMode: state.selectedMode,
      jdText: state.jdText,
      userNotes: state.userNotes,
      activeCvDocumentId: state.activeCvDocumentId,
      demoCvFixture: state.demoCvFixture,
      demoJdFixture: state.demoJdFixture,
      claimConfirmations: state.claimConfirmations,
    }),
  )
}

function defaultState() {
  return {
    bootstrapped: false,
    loading: false,
    healthState: 'connecting',
    healthMessage: 'Checking backend',
    healthDetail: 'Waiting for /api/health.',
    demoOptions: null,
    profile: null,
    analysis: null,
    generatedPack: null,
    surveyDrafts: {},
    claimConfirmations: {},
    selectedMode: 'stretch',
    jdText: '',
    userNotes: '',
    activeCvDocumentId: '',
    demoCvFixture: '',
    demoJdFixture: '',
  }
}

function composeAnswer(draft) {
  const notes = draft.notes.trim()
  return notes ? `${draft.choice_label}. ${notes}`.trim() : draft.choice_label.trim()
}

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    ...defaultState(),
    ...loadPersistedState(),
  }),
  getters: {
    hasAnalysis: (state) => Boolean(state.analysis),
    hasProfile: (state) => Boolean(state.profile?.cv_documents?.length),
    currentJobKey: (state) => {
      if (!state.analysis) return ''
      const jdSnippet = state.jdText.trim().replace(/\s+/g, ' ').slice(0, 120)
      return `${state.analysis.jd_analysis.role_title}:${state.analysis.metadata.jd_label}:${jdSnippet}`
    },
    requiredSurveyQuestions: (state) =>
      (state.analysis?.survey_questions ?? []).filter((question) => question.priority === 'high'),
    answeredSurveyCount() {
      return this.requiredSurveyQuestions.filter(
        (question) => Boolean(this.surveyDrafts[question.requirement_id]?.choice_id),
      ).length
    },
    canAccessDrafts() {
      if (!this.analysis) return false
      if (!this.requiredSurveyQuestions.length) return true
      return this.requiredSurveyQuestions.every((question) =>
        Boolean(this.surveyDrafts[question.requirement_id]?.choice_id),
      )
    },
    selectedCvLabel() {
      return (
        this.profile?.cv_documents?.find((document) => document.id === this.activeCvDocumentId)
          ?.label ?? ''
      )
    },
    claimConfirmationList() {
      return Object.values(this.claimConfirmations)
        .filter((draft) => draft.status !== '')
        .map((draft) => ({
          requirement_id: draft.requirement_id,
          status: draft.status,
          notes: draft.notes.trim(),
        }))
    },
  },
  actions: {
    remember() {
      persistState(this.$state)
    },
    async bootstrap() {
      if (this.bootstrapped) return
      this.healthState = 'connecting'
      this.healthMessage = 'Checking backend'
      this.healthDetail = 'Waiting for /api/health.'
      try {
        const [health, options, profile] = await Promise.all([
          getHealth(),
          getDemoOptions(),
          getProfile(),
        ])
        this.healthState = 'ready'
        this.healthMessage = 'Backend ready'
        this.healthDetail = health.llm_configured
          ? 'Local profile and AI workflow are ready.'
          : 'Local profile and deterministic workflow are ready.'
        this.demoOptions = options
        this.profile = profile
        if (!this.demoCvFixture) this.demoCvFixture = options.default_cv_fixture
        if (!this.demoJdFixture) this.demoJdFixture = options.default_jd_fixture
        if (!this.activeCvDocumentId && profile.cv_documents?.[0]) {
          this.activeCvDocumentId = profile.cv_documents[0].id
        }
      } catch (error) {
        this.healthState = 'unavailable'
        this.healthMessage = 'Backend unavailable'
        this.healthDetail = error instanceof Error ? error.message : 'Backend unavailable.'
      } finally {
        this.bootstrapped = true
        this.remember()
      }
    },
    async refreshProfile() {
      this.profile = await getProfile()
      if (!this.activeCvDocumentId && this.profile.cv_documents?.[0]) {
        this.activeCvDocumentId = this.profile.cv_documents[0].id
      }
      this.remember()
    },
    async importCvs(files) {
      this.profile = await uploadProfileCvs(files)
      if (this.profile.cv_documents?.[0]) {
        this.activeCvDocumentId = this.profile.cv_documents[0].id
      }
      this.remember()
    },
    exportProfile() {
      return exportProfileBundle()
    },
    async importProfile(bundle) {
      this.profile = await importProfileBundle(bundle)
      if (!this.activeCvDocumentId && this.profile.cv_documents?.[0]) {
        this.activeCvDocumentId = this.profile.cv_documents[0].id
      }
      this.remember()
    },
    hydrateSurveyDrafts() {
      const drafts = {}
      const responses = this.profile?.survey_responses ?? []
      for (const question of this.analysis?.survey_questions ?? []) {
        const existing = responses.find(
          (item) =>
            item.job_id === this.currentJobKey && item.requirement_id === question.requirement_id,
        )
        drafts[question.requirement_id] = {
          requirement_id: question.requirement_id,
          requirement_text: question.requirement_text,
          choice_id: existing?.choice_id ?? '',
          choice_label: existing?.choice_label ?? '',
          notes: existing?.notes ?? '',
        }
      }
      this.surveyDrafts = drafts
    },
    hydrateClaimConfirmations() {
      const current = this.claimConfirmations
      const next = {}
      for (const match of this.analysis?.evidence_map ?? []) {
        if (
          match.claim_label === 'Needs User Confirmation' ||
          match.claim_label === 'Stretch Wording' ||
          match.claim_label === 'Unsafe Claim'
        ) {
          next[match.requirement_id] = current[match.requirement_id] ?? {
            requirement_id: match.requirement_id,
            status: '',
            notes: '',
          }
        }
      }
      this.claimConfirmations = next
      this.remember()
    },
    async runSavedCvAnalysis() {
      if (!this.activeCvDocumentId || !this.jdText.trim()) return
      this.loading = true
      try {
        this.analysis = await analyzeSavedCv(
          this.activeCvDocumentId,
          this.jdText.trim(),
          this.selectedMode,
        )
        this.generatedPack = null
        await this.refreshProfile()
        this.hydrateSurveyDrafts()
        this.hydrateClaimConfirmations()
      } finally {
        this.loading = false
      }
    },
    async runUploadAnalysis(file) {
      if (!file || !this.jdText.trim()) return
      this.loading = true
      try {
        this.analysis = await analyzeCv(file, this.jdText.trim(), this.selectedMode)
        this.generatedPack = null
        await this.refreshProfile()
        this.hydrateSurveyDrafts()
        this.hydrateClaimConfirmations()
      } finally {
        this.loading = false
      }
    },
    async runDemoAnalysis() {
      this.loading = true
      try {
        this.analysis = await analyzeDemo(this.demoCvFixture, this.demoJdFixture, this.selectedMode)
        this.generatedPack = null
        this.hydrateSurveyDrafts()
        this.hydrateClaimConfirmations()
      } finally {
        this.loading = false
      }
    },
    setSurveyChoice(question, choiceId, choiceLabel) {
      const current = this.surveyDrafts[question.requirement_id] ?? {
        requirement_id: question.requirement_id,
        requirement_text: question.requirement_text,
        choice_id: '',
        choice_label: '',
        notes: '',
      }
      this.surveyDrafts[question.requirement_id] = {
        ...current,
        choice_id: choiceId,
        choice_label: choiceLabel,
      }
    },
    setSurveyNotes(requirementId, notes) {
      const current = this.surveyDrafts[requirementId]
      if (!current) return
      this.surveyDrafts[requirementId] = { ...current, notes }
    },
    async persistSurveyResponse(question) {
      const draft = this.surveyDrafts[question.requirement_id]
      if (!draft?.choice_id || !this.currentJobKey || this.analysis?.metadata.source === 'demo') {
        return
      }
      this.profile = await saveSurveyResponse(this.currentJobKey, draft)
    },
    setClaimConfirmationStatus(requirementId, status) {
      const current = this.claimConfirmations[requirementId] ?? {
        requirement_id: requirementId,
        status: '',
        notes: '',
      }
      this.claimConfirmations[requirementId] = { ...current, status }
      this.remember()
    },
    setClaimConfirmationNotes(requirementId, notes) {
      const current = this.claimConfirmations[requirementId] ?? {
        requirement_id: requirementId,
        status: '',
        notes: '',
      }
      this.claimConfirmations[requirementId] = { ...current, notes }
      this.remember()
    },
    buildFollowUpAnswers() {
      return Object.values(this.surveyDrafts)
        .filter((draft) => draft.choice_id)
        .map((draft) => ({
          requirement_id: draft.requirement_id,
          answer: composeAnswer(draft),
          skipped: draft.choice_id === 'no-experience' || draft.choice_id === 'not-ready',
        }))
    },
    async runGeneration() {
      if (!this.analysis) return
      this.loading = true
      try {
        this.generatedPack = await generateApplicationPack({
          analysis: this.analysis,
          follow_up_answers: this.buildFollowUpAnswers(),
          user_claim_confirmations: this.claimConfirmationList,
          user_notes: this.userNotes.trim() || undefined,
        })
      } finally {
        this.loading = false
      }
    },
    clearSession() {
      this.analysis = null
      this.generatedPack = null
      this.surveyDrafts = {}
      this.claimConfirmations = {}
    },
  },
})
