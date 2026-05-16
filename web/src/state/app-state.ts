import { reactive, watch } from "vue";

import type {
  AnalysisMode,
  AnalysisResponse,
  DemoOptionsResponse,
  FollowUpAnswer,
  GenerateApplicationPackResponse
} from "../types";

export type HealthState = "connecting" | "ready" | "unavailable";

interface PersistedAppState {
  selectedMode: AnalysisMode;
  jdText: string;
  userNotes: string;
  demoCvFixture: string;
  demoJdFixture: string;
  demoOptions: DemoOptionsResponse | null;
  analysis: AnalysisResponse | null;
  followUpAnswers: Record<string, FollowUpAnswer>;
  generatedPack: GenerateApplicationPackResponse | null;
}

export interface AppState extends PersistedAppState {
  healthState: HealthState;
  healthMessage: string;
  healthDetail: string;
}

const STORAGE_KEY = "haxjobs.app-state.v0.3";
const MAX_PERSIST_BYTES = 220_000;

function defaultState(): AppState {
  return {
    selectedMode: "stretch",
    jdText: "",
    userNotes: "",
    demoCvFixture: "",
    demoJdFixture: "",
    demoOptions: null,
    analysis: null,
    followUpAnswers: {},
    generatedPack: null,
    healthState: "connecting",
    healthMessage: "Checking backend connectivity.",
    healthDetail: "Waiting for /api/health."
  };
}

function loadPersistedState(): Partial<PersistedAppState> {
  if (typeof window === "undefined") {
    return {};
  }
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw) as Partial<PersistedAppState>;
  } catch {
    return {};
  }
}

function persistedSnapshot(state: AppState): PersistedAppState {
  const persistedAnalysis = safelyPersist(state.analysis);
  const persistedPack = safelyPersist(state.generatedPack);
  return {
    selectedMode: state.selectedMode,
    jdText: state.jdText,
    userNotes: state.userNotes,
    demoCvFixture: state.demoCvFixture,
    demoJdFixture: state.demoJdFixture,
    demoOptions: state.demoOptions,
    analysis: persistedAnalysis,
    followUpAnswers: state.followUpAnswers,
    generatedPack: persistedPack
  };
}

function safelyPersist<T>(value: T): T | null {
  if (value === null || value === undefined) {
    return null;
  }
  try {
    const encoded = JSON.stringify(value);
    if (encoded.length > MAX_PERSIST_BYTES) {
      return null;
    }
    return value;
  } catch {
    return null;
  }
}

const initialState = { ...defaultState(), ...loadPersistedState() };

export const appState = reactive<AppState>(initialState);

let persistenceStarted = false;

export function initializeAppStatePersistence(): void {
  if (persistenceStarted || typeof window === "undefined") {
    return;
  }
  persistenceStarted = true;
  watch(
    () => persistedSnapshot(appState),
    (snapshot) => {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    },
    { deep: true, immediate: true }
  );
}

export function setHealthStatus(
  state: HealthState,
  message: string,
  detail: string
): void {
  appState.healthState = state;
  appState.healthMessage = message;
  appState.healthDetail = detail;
}

export function setDemoOptions(options: DemoOptionsResponse): void {
  appState.demoOptions = options;
  if (!appState.demoCvFixture) {
    appState.demoCvFixture = options.default_cv_fixture;
  }
  if (!appState.demoJdFixture) {
    appState.demoJdFixture = options.default_jd_fixture;
  }
}

export function startNewAnalysis(report: AnalysisResponse): void {
  const nextAnswers: Record<string, FollowUpAnswer> = {};
  for (const question of report.follow_up_questions) {
    const existing = appState.followUpAnswers[question.requirement_id];
    nextAnswers[question.requirement_id] = existing ?? {
      requirement_id: question.requirement_id,
      answer: "",
      skipped: false
    };
  }
  appState.analysis = report;
  appState.followUpAnswers = nextAnswers;
  appState.generatedPack = null;
}

export function clearWorkflowResults(): void {
  appState.analysis = null;
  appState.followUpAnswers = {};
  appState.generatedPack = null;
}

export function setFollowUpAnswer(
  requirementId: string,
  update: Partial<FollowUpAnswer>
): void {
  const current = appState.followUpAnswers[requirementId] ?? {
    requirement_id: requirementId,
    answer: "",
    skipped: false
  };
  appState.followUpAnswers[requirementId] = {
    ...current,
    ...update
  };
}

export function setGeneratedPack(pack: GenerateApplicationPackResponse): void {
  appState.generatedPack = pack;
}

export function requiredFollowUpQuestions(): AnalysisResponse["follow_up_questions"] {
  return (appState.analysis?.follow_up_questions ?? []).filter((question) => question.priority === "high");
}

export function hasAnalysis(): boolean {
  return Boolean(appState.analysis);
}

export function hasAnsweredRequirement(requirementId: string): boolean {
  const answer = appState.followUpAnswers[requirementId];
  return Boolean(answer && answer.answer.trim() && !answer.skipped);
}

export function canAccessOutputs(): boolean {
  if (!appState.analysis) {
    return false;
  }
  if (appState.analysis.metadata.mode !== "interview") {
    return true;
  }
  return requiredFollowUpQuestions().every((question) =>
    hasAnsweredRequirement(question.requirement_id)
  );
}

export function answeredFollowUpCount(): number {
  return Object.values(appState.followUpAnswers).filter(
    (answer) => answer.answer.trim() && !answer.skipped
  ).length;
}

export function unresolvedRequiredFollowUpCount(): number {
  return requiredFollowUpQuestions().filter(
    (question) => !hasAnsweredRequirement(question.requirement_id)
  ).length;
}
