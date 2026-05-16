<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import {
  ApiError,
  analyzeCv,
  analyzeDemo,
  getDemoOptions,
  getHealth
} from "./lib/api";
import type {
  AnalysisMode,
  AnalysisResponse,
  DemoFixtureOption,
  DemoOptionsResponse,
  EvidenceMatch
} from "./types";

type HealthState = "connecting" | "ready" | "unavailable";
type ResultFilter = "all" | "strong" | "needs-attention" | "gaps";

const MODE_OPTIONS: Array<{ value: AnalysisMode; label: string }> = [
  { value: "safe", label: "Safe" },
  { value: "stretch", label: "Stretch" },
  { value: "interview", label: "Interview" },
  { value: "ideal", label: "Ideal" }
];
const JD_STORAGE_KEY = "haxjobs.jdText";
const MODE_STORAGE_KEY = "haxjobs.mode";

const selectedFile = ref<File | null>(null);
const jdText = ref("");
const selectedMode = ref<AnalysisMode>("stretch");
const loading = ref(false);
const loadingMessage = ref("");
const errorMessage = ref("");
const copied = ref(false);
const report = ref<AnalysisResponse | null>(null);
const healthState = ref<HealthState>("connecting");
const healthMessage = ref("Checking backend connectivity.");
const healthDetail = ref("");
const demoOptions = ref<DemoOptionsResponse | null>(null);
const demoCvFixture = ref("");
const demoJdFixture = ref("");
const activeFilter = ref<ResultFilter>("all");

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
  jdText.value.trim() ? "" : "Paste the job description text to continue."
);

const isBackendReady = computed(() => healthState.value === "ready");
const uploadDisabledReason = computed(() => {
  if (!isBackendReady.value) {
    return healthDetail.value || healthMessage.value;
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
    return healthDetail.value || healthMessage.value;
  }
  if (!demoCvFixture.value || !demoJdFixture.value) {
    return "Demo fixtures are still loading.";
  }
  return "";
});
const canAnalyze = computed(() => !loading.value && !uploadDisabledReason.value);
const canRunDemo = computed(() => !loading.value && !demoDisabledReason.value);
const currentSummaryText = computed(() => {
  if (!report.value) {
    return "";
  }
  return `${report.value.jd_analysis.role_title}: ${report.value.fit_summary.label} (${report.value.fit_summary.score}/100). ${report.value.fit_summary.summary}`;
});
const matchCounts = computed(() => {
  const counts = {
    "Strong Match": 0,
    "Partial Match": 0,
    "Transferable Match": 0,
    "Weak Match": 0,
    Gap: 0
  };
  for (const match of report.value?.evidence_map ?? []) {
    counts[match.match_label] += 1;
  }
  return counts;
});
const visibleMatches = computed(() => {
  const matches = report.value?.evidence_map ?? [];
  switch (activeFilter.value) {
    case "strong":
      return matches.filter((match) => match.match_label === "Strong Match");
    case "needs-attention":
      return matches.filter((match) =>
        ["Partial Match", "Transferable Match", "Weak Match"].includes(match.match_label)
      );
    case "gaps":
      return matches.filter((match) => match.match_label === "Gap");
    default:
      return matches;
  }
});
const healthLabel = computed(() => {
  if (healthState.value === "ready") {
    return "Backend ready";
  }
  if (healthState.value === "unavailable") {
    return "Backend unavailable";
  }
  return "Connecting";
});

watch(jdText, (value) => sessionStorage.setItem(JD_STORAGE_KEY, value));
watch(selectedMode, (value) => sessionStorage.setItem(MODE_STORAGE_KEY, value));

onMounted(async () => {
  jdText.value = sessionStorage.getItem(JD_STORAGE_KEY) ?? "";
  selectedMode.value = (sessionStorage.getItem(MODE_STORAGE_KEY) as AnalysisMode | null) ?? "stretch";
  await refreshBackendStatus();
});

function humanModeLabel(mode: AnalysisMode): string {
  return MODE_OPTIONS.find((option) => option.value === mode)?.label ?? mode;
}

function applyDemoDefaults(options: DemoOptionsResponse): void {
  demoCvFixture.value = demoCvFixture.value || options.default_cv_fixture;
  demoJdFixture.value = demoJdFixture.value || options.default_jd_fixture;
}

async function refreshBackendStatus(): Promise<void> {
  healthState.value = "connecting";
  healthMessage.value = "Checking backend connectivity.";
  healthDetail.value = "Waiting for /api/health.";
  try {
    const payload = await getHealth();
    healthState.value = "ready";
    healthMessage.value = "Backend ready";
    healthDetail.value = payload.llm_configured
      ? "API reachable and env-backed LLM configuration detected."
      : "API reachable. OPENAI_API_KEY is not loaded, but deterministic analysis still works.";
    const options = await getDemoOptions();
    demoOptions.value = options;
    applyDemoDefaults(options);
  } catch (error) {
    handleApiError(error, { backendFailure: true, fallback: "Backend unavailable." });
  }
}

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
  errorMessage.value = "";
}

function resetForm(): void {
  report.value = null;
  errorMessage.value = "";
  loading.value = false;
  copied.value = false;
  activeFilter.value = "all";
}

async function runAnalysis(): Promise<void> {
  if (!selectedFile.value || !canAnalyze.value) {
    return;
  }
  loading.value = true;
  loadingMessage.value = "Starting analysis for your uploaded CV.";
  errorMessage.value = "";
  try {
    report.value = await analyzeCv(selectedFile.value, jdText.value.trim(), selectedMode.value);
    activeFilter.value = "all";
  } catch (error) {
    handleApiError(error, {
      backendFailure: true,
      fallback: "Analysis failed."
    });
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
  loadingMessage.value = "Starting analysis from built-in demo fixtures.";
  errorMessage.value = "";
  try {
    report.value = await analyzeDemo(demoCvFixture.value, demoJdFixture.value, selectedMode.value);
    activeFilter.value = "all";
  } catch (error) {
    handleApiError(error, {
      backendFailure: true,
      fallback: "Demo analysis failed."
    });
  } finally {
    loading.value = false;
    loadingMessage.value = "";
  }
}

async function copySummary(): Promise<void> {
  if (!currentSummaryText.value) {
    return;
  }
  await navigator.clipboard.writeText(currentSummaryText.value);
  copied.value = true;
  window.setTimeout(() => {
    copied.value = false;
  }, 1500);
}

function downloadFile(filename: string, content: string, type: string): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function downloadJson(): void {
  if (!report.value) {
    return;
  }
  downloadFile(
    "haxjobs-analysis.json",
    JSON.stringify(report.value, null, 2),
    "application/json"
  );
}

function downloadMarkdown(): void {
  if (!report.value) {
    return;
  }
  downloadFile("haxjobs-analysis.md", report.value.markdown_report, "text/markdown");
}

function handleApiError(
  error: unknown,
  options: { backendFailure: boolean; fallback: string }
): void {
  const message = error instanceof Error ? error.message : options.fallback;
  errorMessage.value = message;
  if (options.backendFailure && error instanceof ApiError && error.kind === "backend_unavailable") {
    healthState.value = "unavailable";
    healthMessage.value = "Backend unavailable";
    healthDetail.value = message;
  }
}

function filterChipClass(filter: ResultFilter): string {
  return activeFilter.value === filter ? "filter-chip active" : "filter-chip";
}

function summaryTone(match: EvidenceMatch): string {
  if (match.match_label === "Strong Match") {
    return "success";
  }
  if (match.match_label === "Gap") {
    return "danger";
  }
  return "warning";
}

function fixtureLabel(
  fixtures: DemoFixtureOption[] | undefined,
  fixtureId: string
): string {
  return fixtures?.find((fixture) => fixture.id === fixtureId)?.label ?? fixtureId;
}
</script>

<template>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">HaxJobs / Evidence-first fit check</p>
      <h1>Turn a CV and JD into a defensible fit map before you draft anything.</h1>
      <p class="lede">
        Start local dev with one command, verify backend health immediately, and run either
        your own upload or a built-in demo without touching the CLI first.
      </p>
    </section>

    <section class="status-banner" :data-state="healthState" data-testid="health-banner">
      <div>
        <p class="eyebrow">Backend Status</p>
        <h2>{{ healthLabel }}</h2>
        <p class="status-detail">{{ healthDetail }}</p>
      </div>
      <button class="secondary-button" type="button" @click="refreshBackendStatus">
        Check Again
      </button>
    </section>

    <section v-if="!report" class="panel">
      <div class="card mode-card">
        <div class="card-header">
          <h2>Mode</h2>
          <span class="pill">{{ humanModeLabel(selectedMode) }}</span>
        </div>
        <p class="hint">
          The backend stays deterministic for now, but the mode is tracked in metadata and
          preserved across refreshes.
        </p>
        <label class="mode-select">
          <span>Analysis mode</span>
          <select v-model="selectedMode" data-testid="mode-select">
            <option v-for="option in MODE_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <div class="panel-grid">
        <div class="card card-input">
          <div class="card-header">
            <h2>CV Upload</h2>
            <span class="pill">Accepts PDF or TXT</span>
          </div>
          <label class="upload">
            <input
              data-testid="cv-upload"
              type="file"
              accept=".pdf,.txt"
              @change="handleFileChange"
            />
            <span>{{ selectedFile ? selectedFile.name : "Choose a CV file" }}</span>
            <small>Accepted types: `.pdf`, `.txt`</small>
          </label>
          <p class="hint" :class="{ error: fileError }">
            {{ fileError || "Current file: " + (selectedFile?.name ?? "Nothing selected yet.") }}
          </p>
        </div>

        <div class="card card-input">
          <div class="card-header">
            <h2>Job Description</h2>
            <span class="pill">{{ jdText.length }} chars</span>
          </div>
          <textarea
            data-testid="jd-input"
            v-model="jdText"
            placeholder="Paste the job description here."
            rows="14"
          />
          <p class="hint" :class="{ error: jdError }">
            {{ jdError || "Pasted text is stored in this tab session so a refresh does not wipe it." }}
          </p>
        </div>
      </div>

      <div class="card demo-card">
        <div class="card-header">
          <h2>Run Demo Analysis</h2>
          <span class="pill">Instant local check</span>
        </div>
        <p class="hint">
          Use known fixtures to prove the stack works before you try a real CV upload.
        </p>
        <div class="demo-grid">
          <label>
            <span>Demo CV</span>
            <select v-model="demoCvFixture">
              <option
                v-for="fixture in demoOptions?.cv_fixtures ?? []"
                :key="fixture.id"
                :value="fixture.id"
              >
                {{ fixture.label }}
              </option>
            </select>
          </label>
          <label>
            <span>Demo JD</span>
            <select v-model="demoJdFixture">
              <option
                v-for="fixture in demoOptions?.jd_fixtures ?? []"
                :key="fixture.id"
                :value="fixture.id"
              >
                {{ fixture.label }}
              </option>
            </select>
          </label>
        </div>
        <p class="hint">
          Selected demo: {{ fixtureLabel(demoOptions?.cv_fixtures, demoCvFixture) }} +
          {{ fixtureLabel(demoOptions?.jd_fixtures, demoJdFixture) }}
        </p>
        <div class="actions">
          <button
            data-testid="demo-button"
            class="secondary-button"
            type="button"
            :disabled="!canRunDemo"
            @click="runDemo"
          >
            Run Demo Analysis
          </button>
          <p class="hint" :class="{ error: !!demoDisabledReason }">
            {{ demoDisabledReason || "This uses repo fixtures exposed by the backend whitelist." }}
          </p>
        </div>
      </div>

      <div class="actions action-row">
        <button
          data-testid="analyze-button"
          class="primary-button"
          type="button"
          :disabled="!canAnalyze"
          @click="runAnalysis"
        >
          Analyze Uploaded CV
        </button>
        <p v-if="loadingMessage" class="loading-note">{{ loadingMessage }}</p>
        <p v-if="!loading && uploadDisabledReason" class="hint" :class="{ error: !!uploadDisabledReason }">
          {{ uploadDisabledReason }}
        </p>
        <p v-if="errorMessage" role="alert" class="error-banner">{{ errorMessage }}</p>
      </div>
    </section>

    <section v-else class="panel">
      <div class="card summary-strip">
        <div class="summary-primary">
          <p class="eyebrow">Results</p>
          <h2>{{ report.jd_analysis.role_title }}</h2>
          <p class="lede compact">{{ report.fit_summary.summary }}</p>
        </div>
        <div class="summary-metrics">
          <div class="metric-block">
            <span>Score</span>
            <strong>{{ report.fit_summary.score }}/100</strong>
          </div>
          <div class="metric-block">
            <span>Fit</span>
            <strong>{{ report.fit_summary.label }}</strong>
          </div>
          <div class="metric-block">
            <span>Mode</span>
            <strong>{{ humanModeLabel(report.metadata.mode) }}</strong>
          </div>
          <div class="metric-block">
            <span>Source</span>
            <strong>{{ report.metadata.source }}</strong>
          </div>
        </div>
        <div class="results-actions">
          <button class="secondary-button" type="button" @click="resetForm">
            Analyze Another Role
          </button>
          <button class="secondary-button" type="button" @click="copySummary">
            {{ copied ? "Copied" : "Copy Fit Summary" }}
          </button>
          <button class="primary-button ghost" type="button" @click="downloadJson">
            Download JSON
          </button>
          <button class="primary-button" type="button" @click="downloadMarkdown">
            Download Markdown
          </button>
        </div>
      </div>

      <div class="chip-row">
        <span class="match-chip success">Strong {{ matchCounts["Strong Match"] }}</span>
        <span class="match-chip warning">Partial {{ matchCounts["Partial Match"] }}</span>
        <span class="match-chip warning">Transferable {{ matchCounts["Transferable Match"] }}</span>
        <span class="match-chip warning">Weak {{ matchCounts["Weak Match"] }}</span>
        <span class="match-chip danger">Gaps {{ matchCounts.Gap }}</span>
      </div>

      <div class="card filter-card">
        <div class="card-header">
          <h3>Evidence Map</h3>
          <span class="pill">{{ visibleMatches.length }} visible rows</span>
        </div>
        <div class="filter-row">
          <button :class="filterChipClass('all')" type="button" @click="activeFilter = 'all'">
            All
          </button>
          <button :class="filterChipClass('strong')" type="button" @click="activeFilter = 'strong'">
            Strong
          </button>
          <button
            :class="filterChipClass('needs-attention')"
            type="button"
            @click="activeFilter = 'needs-attention'"
          >
            Needs Attention
          </button>
          <button :class="filterChipClass('gaps')" type="button" @click="activeFilter = 'gaps'">
            Gaps
          </button>
        </div>
        <div class="evidence-list">
          <details
            v-for="match in visibleMatches"
            :key="match.requirement_id"
            class="evidence-row"
            :data-tone="summaryTone(match)"
          >
            <summary>
              <div>
                <p class="requirement-text">{{ match.requirement_text }}</p>
                <p class="meta-line">{{ match.section }} · {{ match.importance }}</p>
              </div>
              <div class="row-pills">
                <span class="match-pill">{{ match.match_label }}</span>
                <span class="claim-pill">{{ match.claim_label }}</span>
              </div>
            </summary>
            <div class="evidence-detail">
              <p><strong>Safe wording:</strong> {{ match.suggested_safe_wording }}</p>
              <p>
                <strong>Supporting evidence:</strong>
                {{ match.supporting_evidence.join(" | ") || "No direct evidence found." }}
              </p>
              <p v-if="match.risk_warning"><strong>Risk warning:</strong> {{ match.risk_warning }}</p>
            </div>
          </details>
          <p v-if="!visibleMatches.length" class="hint">
            No rows match the current filter.
          </p>
        </div>
      </div>

      <div class="results-grid">
        <article class="card">
          <h3>Result Metadata</h3>
          <p><strong>CV:</strong> {{ report.metadata.cv_label }}</p>
          <p><strong>JD:</strong> {{ report.metadata.jd_label }}</p>
          <p>
            <strong>Coverage:</strong>
            {{ report.fit_summary.matched_requirements }}/{{ report.fit_summary.total_requirements }}
          </p>
        </article>

        <article class="card">
          <h3>JD Signals</h3>
          <p>
            <strong>Required:</strong>
            {{ report.jd_analysis.required_skills.join(", ") || "None extracted" }}
          </p>
          <p>
            <strong>Nice to have:</strong>
            {{ report.jd_analysis.desirable_skills.join(", ") || "None extracted" }}
          </p>
          <p>
            <strong>Recruiter concerns:</strong>
            {{ report.jd_analysis.recruiter_concerns.join(", ") || "None extracted" }}
          </p>
        </article>
      </div>

      <div class="results-grid">
        <article class="card">
          <h3>Warnings</h3>
          <ul>
            <li v-for="warning in report.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </article>

        <article class="card">
          <h3>Follow-up Questions</h3>
          <ul>
            <li v-for="question in report.follow_up_questions" :key="question.requirement_id">
              {{ question.question }}
            </li>
          </ul>
        </article>
      </div>
    </section>
  </main>
</template>
