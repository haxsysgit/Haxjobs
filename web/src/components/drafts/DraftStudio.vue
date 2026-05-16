<script setup lang="ts">
import { computed, ref } from "vue";

import { renderSimpleMarkdown } from "../../lib/markdown";
import type { GenerateApplicationPackResponse } from "../../types";

export type DraftDocument = "cv" | "cover-letter" | "interview-notes" | "evidence-map";

const props = defineProps<{
  pack: GenerateApplicationPackResponse;
  activeDocument: DraftDocument;
}>();

const emit = defineEmits<{
  (event: "update:document", value: DraftDocument): void;
}>();
const viewMode = ref<"preview" | "raw">("preview");

const documentBody = computed(() => {
  if (props.activeDocument === "cv") {
    return props.pack.tailored_cv_markdown;
  }
  if (props.activeDocument === "cover-letter") {
    return props.pack.cover_letter_markdown;
  }
  if (props.activeDocument === "interview-notes") {
    return props.pack.interview_notes_markdown;
  }
  return JSON.stringify(props.pack.evidence_map_json, null, 2);
});
const previewAvailable = computed(() => props.activeDocument !== "evidence-map");
const renderedDocumentBody = computed(() =>
  previewAvailable.value ? renderSimpleMarkdown(documentBody.value) : ""
);

const documentLabel = computed(() => {
  if (props.activeDocument === "cv") {
    return "Tailored CV";
  }
  if (props.activeDocument === "cover-letter") {
    return "Cover Letter";
  }
  if (props.activeDocument === "interview-notes") {
    return "Interview Notes";
  }
  return "Evidence Map";
});
</script>

<template>
  <section>
    <div class="stream-actions doc-switcher">
      <button
        class="tab-button"
        :class="{ active: activeDocument === 'cv' }"
        type="button"
        @click="emit('update:document', 'cv')"
      >
        CV
      </button>
      <button
        class="tab-button"
        :class="{ active: activeDocument === 'cover-letter' }"
        type="button"
        @click="emit('update:document', 'cover-letter')"
      >
        Cover Letter
      </button>
      <button
        class="tab-button"
        :class="{ active: activeDocument === 'interview-notes' }"
        type="button"
        @click="emit('update:document', 'interview-notes')"
      >
        Interview Notes
      </button>
      <button
        class="tab-button"
        :class="{ active: activeDocument === 'evidence-map' }"
        type="button"
        @click="emit('update:document', 'evidence-map')"
      >
        Evidence Map
      </button>
      <button
        v-if="previewAvailable"
        class="tab-button"
        :class="{ active: viewMode === 'preview' }"
        type="button"
        @click="viewMode = 'preview'"
      >
        Preview
      </button>
      <button
        v-if="previewAvailable"
        class="tab-button"
        :class="{ active: viewMode === 'raw' }"
        type="button"
        @click="viewMode = 'raw'"
      >
        Raw
      </button>
    </div>

    <p class="status-line">{{ documentLabel }} · {{ pack.metadata.source }} · {{ pack.metadata.mode }}</p>

    <article
      v-if="previewAvailable && viewMode === 'preview'"
      class="document-surface markdown-body"
      data-testid="document-rendered"
      v-html="renderedDocumentBody"
    />
    <pre v-else class="document-preview" data-testid="document-preview">{{ documentBody }}</pre>
  </section>
</template>
