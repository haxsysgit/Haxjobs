<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError, analyzeCv, analyzeDemo, getDemoOptions, getHealth } from "../lib/api";
import {
  appState,
  canAccessOutputs,
  clearWorkflowResults,
  hasAnalysis,
  setDemoOptions,
  setHealthStatus,
  startNewAnalysis
} from "../state/app-state";
import type { AnalysisMode } from "../types";

const router = useRouter();

const MODE_OPTIONS: Array<{ value: AnalysisMode; label: string }> = [
  { value: "safe", label: "Safe" },
  { value: "stretch", label: "Stretch" },
  { value: "interview", label: "Interview" },
  { value: "ideal", label: "Ideal" }
];

const selectedFile = ref<File | null>(null);
const loading = ref(false);
const loadingMessage = ref("");
const errorMessage = ref("");
const demoErrorMessage = ref("");

const fileError = computed(() => {
  if (!selectedFile.value) {
    return "Upload a CV as PDF or TXT.";
  }
  const valid = [".pdf", ".txt"].some((suffix) =>
    selectedFile.value?.name.toLowerCase().endsWith(suffix)
  );
  return valid ? "" : "Invalid CV file. Upload a PDF or plain-text `.txt` file.";
});
const jdError = computed(() =>
  appState.jdText.trim() ? "" : "Paste the job description text to continue."
);
const isBackendReady = computed(() => appState.healthState === "ready");
const uploadDisabledReason = computed(() => {
  if (!isBackendReady.value) {
    return appState.healthDetail || appState.healthMessage;
  }
  if (fileError.value) {
    return fileError.value;
  }
  if (jdError.value) {
    return jdError.value;
  }
  return "";
});
const demoDisabledReason = computed(() => {
  if (!isBackendReady.value) {
    return appState.healthDetail || appState.healthMessage;
  }
  if (!appState.demoCvFixture || !appState.demoJdFixture) {
    return "Demo fixtures are still loading.";
  }
  return "";
});
const canAnalyze = computed(() => !loading.value && !uploadDisabledReason.value);
const canRunDemo = computed(() => !loading.value && !demoDisabledReason.value);
const hasSavedSession = computed(() => hasAnalysis());
const resumeDestination = computed(() => (canAccessOutputs() ? "/drafts" : "/review"));
const resumeLabel = computed(() => (canAccessOutputs() ? "Resume Drafts" : "Resume Review"));
const showBackendFailureBanner = computed(() => appState.healthState === "unavailable");

onMounted(async () => {
  await refreshBackendStatus();
});

async function refreshBackendStatus(): Promise<void> {
  setHealthStatus("connecting", "Checking backend connectivity.", "Waiting for /api/health.");
  try {
    const payload = await getHealth();
    setHealthStatus(
      "ready",
      "Backend ready",
      payload.llm_configured
        ? "API reachable. Local environment is loaded."
        : "API reachable. Deterministic workflow is ready."
    );
    const options = await getDemoOptions();
    setDemoOptions(options);
  } catch (error) {
    handleApiError(error, { backendFailure: true, fallback: "Backend unavailable.", target: "main" });
  }
}

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
  errorMessage.value = "";
}

function handleApiError(
  error: unknown,
  options: { backendFailure: boolean; fallback: string; target: "main" | "demo" }
): void {
  const message = error instanceof Error ? error.message : options.fallback;
  if (options.target === "demo") {
    demoErrorMessage.value = message;
  } else {
    errorMessage.value = message;
  }
  if (options.backendFailure && error instanceof ApiError && error.kind === "backend_unavailable") {
    setHealthStatus("unavailable", "Backend unavailable", message);
  }
}

async function runAnalysis(): Promise<void> {
  if (!selectedFile.value || !canAnalyze.value) {
    return;
  }
  loading.value = true;
  loadingMessage.value = "Running analysis.";
  errorMessage.value = "";
  demoErrorMessage.value = "";
  clearWorkflowResults();
  try {
    const report = await analyzeCv(selectedFile.value, appState.jdText.trim(), appState.selectedMode);
    startNewAnalysis(report);
    await router.push("/review");
  } catch (error) {
    handleApiError(error, { backendFailure: true, fallback: "Analysis failed.", target: "main" });
  } finally {
    loading.value = false;
    loadingMessage.value = "";
  }
}

async function runDemo(): Promise<void> {
  if (!canRunDemo.value) {
    return;
  }
  loading.value = true;
  loadingMessage.value = "Running demo.";
  errorMessage.value = "";
  demoErrorMessage.value = "";
  clearWorkflowResults();
  try {
    const report = await analyzeDemo(
      appState.demoCvFixture,
      appState.demoJdFixture,
      appState.selectedMode
    );
    startNewAnalysis(report);
    await router.push("/review");
  } catch (error) {
    handleApiError(error, { backendFailure: true, fallback: "Demo analysis failed.", target: "demo" });
  } finally {
    loading.value = false;
    loadingMessage.value = "";
  }
}

function fixtureLabel(type: "cv_fixtures" | "jd_fixtures", fixtureId: string): string {
  return appState.demoOptions?.[type].find((fixture) => fixture.id === fixtureId)?.label ?? fixtureId;
}

function startFreshSession(): void {
  selectedFile.value = null;
  clearWorkflowResults();
  errorMessage.value = "";
  demoErrorMessage.value = "";
}
</script>

<template>
  <section class="page-stream">
    <header class="stream-header">
      <h2>Workspace</h2>
      <div v-if="hasSavedSession" class="stream-actions">
        <button class="secondary-button" type="button" @click="router.push(resumeDestination)">
          {{ resumeLabel }}
        </button>
        <button class="secondary-button" type="button" @click="startFreshSession">Start Fresh</button>
      </div>
    </header>

    <section
      v-if="showBackendFailureBanner"
      class="inline-alert"
      :data-state="appState.healthState"
      data-testid="health-banner"
    >
      <p>{{ appState.healthDetail || appState.healthMessage }}</p>
      <button class="secondary-button" type="button" @click="refreshBackendStatus">Retry</button>
    </section>

    <section id="intake" class="stream-block">
      <h3>Intake</h3>
      <div class="field">
        <span>CV file</span>
        <label class="upload">
          <input
            data-testid="cv-upload"
            type="file"
            accept=".pdf,.txt"
            @change="handleFileChange"
          />
          <span>{{ selectedFile ? selectedFile.name : "Choose a CV file" }}</span>
          <small>PDF or TXT</small>
        </label>
      </div>
      <label class="field">
        <span>Job description</span>
        <textarea
          data-testid="jd-input"
          v-model="appState.jdText"
          rows="14"
          placeholder="Paste the job description here."
        />
      </label>
      <div class="stream-actions">
        <button
          data-testid="analyze-button"
          class="primary-button"
          type="button"
          :disabled="!canAnalyze"
          @click="runAnalysis"
        >
          Run Analysis
        </button>
      </div>
      <p class="status-line">{{ loadingMessage || uploadDisabledReason || "Ready." }}</p>
      <p v-if="errorMessage" role="alert" class="error-banner">{{ errorMessage }}</p>
    </section>

    <details id="advanced" class="stream-block collapsible">
      <summary>Advanced</summary>
      <label class="field">
        <span>Analysis mode</span>
        <select v-model="appState.selectedMode" data-testid="mode-select">
          <option v-for="option in MODE_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
      <label class="field">
        <span>Notes for drafting</span>
        <textarea
          v-model="appState.userNotes"
          rows="4"
          placeholder="Optional context for final drafts."
        />
      </label>
    </details>

    <details id="demo" class="stream-block collapsible">
      <summary>Demo</summary>
      <label class="field">
        <span>CV fixture</span>
        <select v-model="appState.demoCvFixture">
          <option
            v-for="fixture in appState.demoOptions?.cv_fixtures ?? []"
            :key="fixture.id"
            :value="fixture.id"
          >
            {{ fixture.label }}
          </option>
        </select>
      </label>
      <label class="field">
        <span>JD fixture</span>
        <select v-model="appState.demoJdFixture">
          <option
            v-for="fixture in appState.demoOptions?.jd_fixtures ?? []"
            :key="fixture.id"
            :value="fixture.id"
          >
            {{ fixture.label }}
          </option>
        </select>
      </label>
      <div class="stream-actions">
        <button
          data-testid="demo-button"
          class="secondary-button"
          type="button"
          :disabled="!canRunDemo"
          @click="runDemo"
        >
          Run Demo
        </button>
      </div>
      <p class="status-line">
        {{ fixtureLabel("cv_fixtures", appState.demoCvFixture) }} +
        {{ fixtureLabel("jd_fixtures", appState.demoJdFixture) }}
      </p>
      <p class="status-line">{{ demoDisabledReason || "Ready." }}</p>
      <p v-if="demoErrorMessage" role="alert" class="error-banner">{{ demoErrorMessage }}</p>
    </details>
  </section>
</template>
