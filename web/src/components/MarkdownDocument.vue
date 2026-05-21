<script setup>
import { computed } from 'vue'

const props = defineProps({
  markdown: {
    type: String,
    default: '',
  },
})

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function inline(value) {
  return escapeHtml(value).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

const rendered = computed(() => {
  const lines = props.markdown.split(/\r?\n/)
  const html = []
  let inList = false

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      if (inList) {
        html.push('</ul>')
        inList = false
      }
      continue
    }
    if (trimmed.startsWith('### ')) {
      if (inList) html.push('</ul>')
      inList = false
      html.push(`<h3>${inline(trimmed.slice(4))}</h3>`)
    } else if (trimmed.startsWith('## ')) {
      if (inList) html.push('</ul>')
      inList = false
      html.push(`<h2>${inline(trimmed.slice(3))}</h2>`)
    } else if (trimmed.startsWith('# ')) {
      if (inList) html.push('</ul>')
      inList = false
      html.push(`<h1>${inline(trimmed.slice(2))}</h1>`)
    } else if (trimmed.startsWith('- ')) {
      if (!inList) {
        html.push('<ul>')
        inList = true
      }
      html.push(`<li>${inline(trimmed.slice(2))}</li>`)
    } else {
      if (inList) {
        html.push('</ul>')
        inList = false
      }
      html.push(`<p>${inline(trimmed)}</p>`)
    }
  }

  if (inList) html.push('</ul>')
  return html.join('')
})
</script>

<template>
  <article class="document-rendered" data-testid="document-rendered" v-html="rendered"></article>
</template>
