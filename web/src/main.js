import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'

import App from './App.vue'
import { createHaxjobsRouter } from './router'
import { pinia } from './stores/pinia'
import './style.css'

const app = createApp(App)

app.use(pinia)
app.use(createHaxjobsRouter())
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.hax-dark-mode',
      cssLayer: false,
    },
  },
  ripple: true,
  inputVariant: 'filled',
})

app.mount('#app')
