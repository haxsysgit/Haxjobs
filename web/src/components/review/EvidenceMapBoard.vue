<script setup lang="ts">
import { computed } from "vue";

import type { AnalysisResponse, EvidenceMatch } from "../../types";

export type ResultFilter = "all" | "strong" | "needs-attention" | "gaps";

const props = defineProps<{
  report: AnalysisResponse;
  filter: ResultFilter;
  focusRequirementId: string | null;
}>();

const emit = defineEmits<{
  (event: "update:filter", value: ResultFilter): void;
}>();

const visibleMatches = computed(() => {
  switch (props.filter) {
    case "strong":
      return props.report.evidence_map.filter((match) => match.match_label === "Strong Match");
    case "needs-attention":
      return props.report.evidence_map.filter((match) =>
        ["Partial Match", "Transferable Match", "Weak Match"].includes(match.match_label)
      );
    case "gaps":
      return props.report.evidence_map.filter((match) => match.match_label === "Gap");
    default:
      return props.report.evidence_map;
  }
});

function summaryTone(match: EvidenceMatch): string {
  if (match.match_label === "Strong Match") {
    return "success";
  }
  if (match.match_label === "Gap") {
    return "danger";
  }
  return "warning";
}

function filterChipClass(filter: ResultFilter): string {
  return props.filter === filter ? "filter-chip active" : "filter-chip";
}

function rowClass(match: EvidenceMatch): string {
  if (props.focusRequirementId && props.focusRequirementId === match.requirement_id) {
    return "evidence-row focused";
  }
  return "evidence-row";
}
</script>

<template>
  <section>
    <div class="stream-actions">
      <button :class="filterChipClass('all')" type="button" @click="emit('update:filter', 'all')">All</button>
      <button :class="filterChipClass('strong')" type="button" @click="emit('update:filter', 'strong')">Strong</button>
      <button
        :class="filterChipClass('needs-attention')"
        type="button"
        @click="emit('update:filter', 'needs-attention')"
      >
        Attention
      </button>
      <button :class="filterChipClass('gaps')" type="button" @click="emit('update:filter', 'gaps')">Gaps</button>
    </div>

    <p class="status-line">{{ visibleMatches.length }} requirement rows</p>

    <details
      v-for="match in visibleMatches"
      :id="`evidence-${match.requirement_id}`"
      :key="match.requirement_id"
      :class="rowClass(match)"
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
        <p><strong>Supporting evidence:</strong> {{ match.supporting_evidence.join(" | ") || "No direct evidence found." }}</p>
        <p v-if="match.risk_warning"><strong>Risk warning:</strong> {{ match.risk_warning }}</p>
      </div>
    </details>

    <p v-if="!visibleMatches.length" class="status-line">No rows match the current filter.</p>
  </section>
</template>
