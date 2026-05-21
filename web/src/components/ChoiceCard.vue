<script setup>
defineProps({
  selected: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <button class="choice-card" :class="{ selected }" type="button">
    <span class="choice-dot" aria-hidden="true"></span>
    <span>
      <strong>{{ title }}</strong>
      <small v-if="description">{{ description }}</small>
    </span>
  </button>
</template>
