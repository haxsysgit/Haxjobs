<script setup lang="ts">
import { computed } from "vue";

import {
  answeredFollowUpCount,
  appState,
  hasAnsweredRequirement,
  requiredFollowUpQuestions,
  setFollowUpAnswer
} from "../../state/app-state";
import type { AnalysisResponse, FollowUpQuestion } from "../../types";

const props = defineProps<{
  report: AnalysisResponse;
}>();

const emit = defineEmits<{
  (event: "openRequirement", requirementId: string): void;
}>();

const requiredCount = computed(() => requiredFollowUpQuestions().length);
const answeredCount = computed(() => answeredFollowUpCount());

function answerValue(question: FollowUpQuestion): string {
  return appState.followUpAnswers[question.requirement_id]?.answer ?? "";
}

function skipped(question: FollowUpQuestion): boolean {
  return appState.followUpAnswers[question.requirement_id]?.skipped ?? false;
}

function updateAnswer(question: FollowUpQuestion, value: string): void {
  setFollowUpAnswer(question.requirement_id, {
    requirement_id: question.requirement_id,
    answer: value,
    skipped: false
  });
}

function toggleSkip(question: FollowUpQuestion): void {
  const current = skipped(question);
  setFollowUpAnswer(question.requirement_id, {
    requirement_id: question.requirement_id,
    skipped: !current,
    answer: current ? answerValue(question) : ""
  });
}

function priorityClass(priority: FollowUpQuestion["priority"]): string {
  return `question-card priority-${priority}`;
}
</script>

<template>
  <section>
    <h3>Follow-up Questions</h3>
    <p class="status-line">{{ answeredCount }} / {{ requiredCount }} required answered</p>

    <div v-if="props.report.follow_up_questions.length" class="question-stack">
      <article
        v-for="question in props.report.follow_up_questions"
        :key="question.requirement_id"
        :class="priorityClass(question.priority)"
      >
        <div class="stream-header">
          <div>
            <p class="meta-line">{{ question.priority }} priority</p>
            <p class="requirement-text">{{ question.requirement_text }}</p>
          </div>
          <span class="pill">
            {{
              hasAnsweredRequirement(question.requirement_id)
                ? "Answered"
                : skipped(question)
                  ? "Skipped"
                  : "Open"
            }}
          </span>
        </div>
        <p>{{ question.question }}</p>
        <p class="meta-line">{{ question.reason }}</p>
        <textarea
          :value="answerValue(question)"
          rows="4"
          placeholder="Add a specific example you can defend in interview."
          @input="updateAnswer(question, ($event.target as HTMLTextAreaElement).value)"
        />
        <div class="stream-actions">
          <button class="secondary-button" type="button" @click="toggleSkip(question)">
            {{ skipped(question) ? "Undo Skip" : "Skip" }}
          </button>
          <button
            class="secondary-button"
            type="button"
            @click="emit('openRequirement', question.requirement_id)"
          >
            Show Evidence
          </button>
        </div>
      </article>
    </div>

    <p v-else class="status-line">No follow-up questions were generated.</p>
  </section>
</template>
