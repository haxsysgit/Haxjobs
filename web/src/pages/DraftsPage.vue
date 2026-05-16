<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter, useRoute } from "vue-router";

import DraftStudio, { type DraftDocument } from "../components/drafts/DraftStudio.vue";
import { ApiError, generateApplicationPack } from "../lib/api";
import { renderSimpleMarkdown } from "../lib/markdown";
import { appState, setGeneratedPack } from "../state/app-state";

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const errorMessage = ref("");
const copied = ref(false);
const aspirationalDocument = ref<"cv" | "cover-letter" | "interview-notes">("cv");

const report = computed(() => appState.analysis);
const pack = computed(() => appState.generatedPack);
const aspirationalPack = computed(() => report.value?.aspirational_pack ?? null);
const activeDocument = computed<DraftDocument>(() => {
  const doc = route.query.doc;
  if (doc === "cv" || doc === "cover-letter" || doc === "interview-notes" || doc === "evidence-map") {
    return doc;
  }
  return "cv";
});

const answerList = computed(() =>
  Object.values(appState.followUpAnswers).sort((left, right) =>
    left.requirement_id.localeCompare(right.requirement_id)
  )
);
const generationLabel = computed(() => (pack.value ? "Refresh" : "Generate"));
const aspirationalBody = computed(() => {
  if (!aspirationalPack.value) {
    return "";
  }
  if (aspirationalDocument.value === "cv") {
    return aspirationalPack.value.tailored_cv_markdown;
  }
  if (aspirationalDocument.value === "cover-letter") {
    return aspirationalPack.value.cover_letter_markdown;
  }
  return aspirationalPack.value.interview_notes_markdown;
});
const renderedAspirationalBody = computed(() =>
  aspirationalBody.value ? renderSimpleMarkdown(aspirationalBody.value) : ""
);

function setDocument(value: DraftDocument): void {
  router.replace({
    path: "/drafts",
    query: {
      ...route.query,
      doc: value
    }
  });
}

async function runGeneration(): Promise<void> {
  if (!report.value || loading.value) {
    return;
  }
  loading.value = true;
  errorMessage.value = "";
  try {
    const response = await generateApplicationPack({
      analysis: report.value,
      follow_up_answers: answerList.value,
      user_notes: appState.userNotes.trim() || undefined
    });
    setGeneratedPack(response);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError || error instanceof Error
        ? error.message
        : "Output generation failed.";
  } finally {
    loading.value = false;
  }
}

function currentDocument(): string {
  if (!pack.value) {
    return "";
  }
  if (activeDocument.value === "cv") {
    return pack.value.tailored_cv_markdown;
  }
  if (activeDocument.value === "cover-letter") {
    return pack.value.cover_letter_markdown;
  }
  if (activeDocument.value === "interview-notes") {
    return pack.value.interview_notes_markdown;
  }
  return JSON.stringify(pack.value.evidence_map_json, null, 2);
}

function currentFilename(): string {
  if (activeDocument.value === "cv") {
    return "tailored_cv.md";
  }
  if (activeDocument.value === "cover-letter") {
    return "cover_letter.md";
  }
  if (activeDocument.value === "interview-notes") {
    return "interview_notes.md";
  }
  return "evidence_map.json";
}

async function copyCurrentDocument(): Promise<void> {
  const content = currentDocument();
  if (!content) {
    return;
  }
  await navigator.clipboard.writeText(content);
  copied.value = true;
  window.setTimeout(() => {
    copied.value = false;
  }, 1200);
}

function downloadCurrentDocument(): void {
  const content = currentDocument();
  if (!content) {
    return;
  }
  const type = activeDocument.value === "evidence-map" ? "application/json" : "text/markdown";
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = currentFilename();
  anchor.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <section v-if="report" class="page-stream">
    <header class="stream-header">
      <h2>Drafts</h2>
      <div class="stream-actions">
        <button class="primary-button" type="button" :disabled="loading" @click="runGeneration">
          {{ generationLabel }}
        </button>
        <button
          class="secondary-button"
          type="button"
          :disabled="!pack"
          data-testid="copy-output-button"
          @click="copyCurrentDocument"
        >
          {{ copied ? "Copied" : "Copy" }}
        </button>
        <button
          class="secondary-button"
          type="button"
          :disabled="!pack"
          data-testid="download-output-button"
          @click="downloadCurrentDocument"
        >
          Download
        </button>
      </div>
    </header>

    <p class="status-line">
      {{ report.jd_analysis.role_title }} · {{ report.metadata.mode }} · {{ report.fit_summary.score }}/100
    </p>
    <p v-if="loading" class="status-line">Generating pack.</p>
    <p v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</p>

    <section id="documents" class="stream-block draft-stream">
      <DraftStudio
        v-if="pack"
        :pack="pack"
        :active-document="activeDocument"
        @update:document="setDocument"
      />
      <p v-else class="status-line">Generate once to open documents.</p>
    </section>

    <section id="aspirational" class="stream-block" v-if="aspirationalPack">
      <h3>Aspirational Sample</h3>
      <p class="status-line">
        {{ aspirationalPack.label }} · model {{ aspirationalPack.model_tier }}
      </p>
      <div class="stream-actions">
        <button
          class="tab-button"
          :class="{ active: aspirationalDocument === 'cv' }"
          type="button"
          @click="aspirationalDocument = 'cv'"
        >
          CV
        </button>
        <button
          class="tab-button"
          :class="{ active: aspirationalDocument === 'cover-letter' }"
          type="button"
          @click="aspirationalDocument = 'cover-letter'"
        >
          Cover Letter
        </button>
        <button
          class="tab-button"
          :class="{ active: aspirationalDocument === 'interview-notes' }"
          type="button"
          @click="aspirationalDocument = 'interview-notes'"
        >
          Interview Notes
        </button>
      </div>
      <article
        class="document-surface markdown-body"
        data-testid="aspirational-rendered"
        v-html="renderedAspirationalBody"
      />
    </section>
  </section>
</template>
