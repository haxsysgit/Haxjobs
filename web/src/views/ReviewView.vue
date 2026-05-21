<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import { ArrowRight, ShieldAlert } from '@lucide/vue'

import ChoiceCard from '../components/ChoiceCard.vue'
import { useWorkspaceStore } from '../stores/workspace'

const router = useRouter()
const workspace = useWorkspaceStore()

const evidenceByRequirement = computed(() => {
  const map = new Map()
  for (const match of workspace.analysis?.evidence_map ?? []) {
    map.set(match.requirement_id, match)
  }
  return map
})

const confirmationMatches = computed(() =>
  (workspace.analysis?.evidence_map ?? []).filter((match) =>
    ['Needs User Confirmation', 'Stretch Wording', 'Unsafe Claim'].includes(match.claim_label),
  ),
)

const fitScore = computed(() => workspace.analysis?.evaluator_assessment?.fit_score ?? workspace.analysis?.fit_summary?.score)

async function chooseSurvey(question, choice) {
  workspace.setSurveyChoice(question, choice.id, choice.label)
  await workspace.persistSurveyResponse(question)
}

function openDrafts() {
  if (workspace.canAccessDrafts) router.push('/drafts')
}
</script>

<template>
  <div v-if="workspace.analysis" class="review-layout">
    <section class="review-main">
      <div class="review-header">
        <div>
          <p class="context-kicker">Guided review</p>
          <h2>Add only the details that improve the draft</h2>
          <p>{{ workspace.analysis.fit_summary.summary }}</p>
        </div>
        <Button :disabled="!workspace.canAccessDrafts" @click="openDrafts">
          Open Pack
          <ArrowRight :size="17" />
        </Button>
      </div>

      <article
        v-for="(question, index) in workspace.analysis.survey_questions"
        :key="question.requirement_id"
        class="numbered-section"
      >
        <div class="section-label">
          <span class="section-number">{{ String(index + 1).padStart(2, '0') }}</span>
          {{ question.priority }} priority
        </div>
        <h3>{{ question.requirement_text }}</h3>
        <p>{{ question.prompt }}</p>

        <div class="choice-grid">
          <ChoiceCard
            v-for="choice in question.choices"
            :key="choice.id"
            :title="choice.label"
            :description="choice.description"
            :selected="workspace.surveyDrafts[question.requirement_id]?.choice_id === choice.id"
            @click="chooseSurvey(question, choice)"
          />
        </div>

        <Textarea
          v-if="question.allow_notes"
          :model-value="workspace.surveyDrafts[question.requirement_id]?.notes ?? ''"
          rows="3"
          class="full-control notes-input"
          placeholder="Add a concrete example, metric, or boundary if useful."
          @update:model-value="workspace.setSurveyNotes(question.requirement_id, $event)"
          @blur="workspace.persistSurveyResponse(question)"
        />

        <aside v-if="evidenceByRequirement.get(question.requirement_id)" class="quiet-evidence">
          <strong>{{ evidenceByRequirement.get(question.requirement_id).claim_label }}</strong>
          <span>{{ evidenceByRequirement.get(question.requirement_id).suggested_safe_wording }}</span>
        </aside>
      </article>

      <article v-if="confirmationMatches.length" class="numbered-section">
        <div class="section-label">
          <span class="section-number">C</span>
          Claim safety
        </div>
        <h3>Keep strong wording believable</h3>
        <p>Confirm, soften, or reject claims that need a human check before generation.</p>

        <div v-for="match in confirmationMatches" :key="match.requirement_id" class="claim-row">
          <div>
            <h4>{{ match.requirement_text }}</h4>
            <p>{{ match.risk_warning ?? match.suggested_safe_wording }}</p>
          </div>
          <div class="choice-grid compact">
            <ChoiceCard
              title="Confirmed"
              description="I can defend this."
              :selected="workspace.claimConfirmations[match.requirement_id]?.status === 'confirmed'"
              @click="workspace.setClaimConfirmationStatus(match.requirement_id, 'confirmed')"
            />
            <ChoiceCard
              title="Uncertain"
              description="Use careful wording."
              :selected="workspace.claimConfirmations[match.requirement_id]?.status === 'uncertain'"
              @click="workspace.setClaimConfirmationStatus(match.requirement_id, 'uncertain')"
            />
            <ChoiceCard
              title="Rejected"
              description="Do not use this."
              :selected="workspace.claimConfirmations[match.requirement_id]?.status === 'rejected'"
              @click="workspace.setClaimConfirmationStatus(match.requirement_id, 'rejected')"
            />
          </div>
        </div>
      </article>
    </section>

    <aside class="review-aside">
      <section class="signal-panel">
        <div class="score-mark">{{ fitScore }}</div>
        <h3>{{ workspace.analysis.fit_summary.label }}</h3>
        <p>{{ workspace.analysis.recruiter_assessment?.shortlist_summary ?? workspace.analysis.fit_summary.summary }}</p>
      </section>

      <section class="signal-panel">
        <h3>Recruiter signals</h3>
        <ul>
          <li v-for="item in workspace.analysis.recruiter_assessment?.priority_requirements ?? []" :key="item">
            {{ item }}
          </li>
        </ul>
      </section>

      <section class="signal-panel warning">
        <ShieldAlert :size="18" aria-hidden="true" />
        <h3>Evaluator notes</h3>
        <p>{{ workspace.analysis.evaluator_assessment?.summary ?? 'No evaluator warning returned.' }}</p>
      </section>
    </aside>
  </div>
</template>
