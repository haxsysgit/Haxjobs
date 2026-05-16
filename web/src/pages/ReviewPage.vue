<script setup lang="ts">
import { computed } from "vue";
import { useRouter, useRoute } from "vue-router";

import EvidenceMapBoard, {
  type ResultFilter
} from "../components/review/EvidenceMapBoard.vue";
import FollowUpQuestionsPanel from "../components/review/FollowUpQuestionsPanel.vue";
import {
  appState,
  canAccessOutputs,
  unresolvedRequiredFollowUpCount
} from "../state/app-state";

type ReviewPanel = "evidence" | "questions";

const router = useRouter();
const route = useRoute();

const report = computed(() => appState.analysis);
const activePanel = computed<ReviewPanel>(() => {
  const panel = route.query.panel;
  if (panel === "questions") {
    return "questions";
  }
  return "evidence";
});
const activeFilter = computed<ResultFilter>(() => {
  const filter = route.query.filter;
  if (
    filter === "strong" ||
    filter === "needs-attention" ||
    filter === "gaps" ||
    filter === "all"
  ) {
    return filter;
  }
  return "all";
});
const focusRequirementId = computed(() => {
  const value = route.query.focus;
  return typeof value === "string" && value ? value : null;
});

const canOpenDrafts = computed(() => canAccessOutputs());
const recruiterAssessment = computed(() => report.value?.recruiter_assessment);
const evaluatorAssessment = computed(() => report.value?.evaluator_assessment);
const verificationQuestions = computed(() => report.value?.verification_questions ?? []);

function setPanel(panel: ReviewPanel): void {
  router.replace({
    path: "/review",
    query: {
      ...route.query,
      panel
    }
  });
}

function setFilter(value: ResultFilter): void {
  router.replace({
    path: "/review",
    query: {
      ...route.query,
      panel: "evidence",
      filter: value
    }
  });
}

function openRequirement(requirementId: string): void {
  router.replace({
    path: "/review",
    query: {
      ...route.query,
      panel: "evidence",
      focus: requirementId
    }
  });
}
</script>

<template>
  <section v-if="report" class="page-stream">
    <header class="stream-header">
      <h2>Review</h2>
      <div class="stream-actions">
        <button class="secondary-button" type="button" @click="router.push('/')">Workspace</button>
        <button class="primary-button" type="button" :disabled="!canOpenDrafts" @click="router.push('/drafts')">
          Drafts
        </button>
      </div>
    </header>

    <p class="status-line">
      {{ report.jd_analysis.role_title }} · Score {{ report.fit_summary.score }}/100 ·
      {{ report.fit_summary.matched_requirements }}/{{ report.fit_summary.total_requirements }} matched
    </p>
    <p v-if="!canOpenDrafts" class="status-line error-banner">
      Drafts locked until {{ unresolvedRequiredFollowUpCount() }} required answer(s) are filled.
    </p>

    <section id="ai" class="stream-block" v-if="recruiterAssessment || evaluatorAssessment">
      <h3>AI Pass</h3>
      <p class="status-line">Engine {{ report.analysis_engine }} · Demo-ready structured JSON stages</p>
      <div class="ai-grid">
        <article class="info-panel" v-if="recruiterAssessment">
          <p class="panel-label">Recruiter</p>
          <p>{{ recruiterAssessment.shortlist_summary }}</p>
          <p class="status-line">
            {{ recruiterAssessment.priority_requirements.slice(0, 3).join(" · ") }}
          </p>
        </article>
        <article class="info-panel" v-if="evaluatorAssessment">
          <p class="panel-label">Evaluator</p>
          <p>{{ evaluatorAssessment.summary }}</p>
          <p class="status-line">
            {{ evaluatorAssessment.uncertain_claims.length }} uncertain ·
            {{ evaluatorAssessment.weak_claims.length }} flagged
          </p>
        </article>
      </div>
      <article class="info-panel" v-if="verificationQuestions.length">
        <p class="panel-label">Verification</p>
        <p class="status-line">Top prompts from the verification stage</p>
        <ul class="compact-list">
          <li v-for="question in verificationQuestions.slice(0, 3)" :key="question.requirement_id">
            {{ question.question }}
          </li>
        </ul>
      </article>
    </section>

    <section class="stream-actions">
      <button
        class="filter-chip"
        :class="{ active: activePanel === 'evidence' }"
        type="button"
        @click="setPanel('evidence')"
      >
        Evidence
      </button>
      <button
        class="filter-chip"
        :class="{ active: activePanel === 'questions' }"
        type="button"
        @click="setPanel('questions')"
      >
        Questions
      </button>
    </section>

    <section id="evidence" v-show="activePanel === 'evidence'" class="stream-block">
      <EvidenceMapBoard
        :report="report"
        :filter="activeFilter"
        :focus-requirement-id="focusRequirementId"
        @update:filter="setFilter"
      />
    </section>

    <section id="questions" v-show="activePanel === 'questions'" class="stream-block">
      <FollowUpQuestionsPanel :report="report" @open-requirement="openRequirement" />
    </section>
  </section>
</template>
