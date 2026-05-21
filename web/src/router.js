import { createRouter, createWebHistory } from 'vue-router'

import DraftsView from './views/DraftsView.vue'
import ReviewView from './views/ReviewView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import { pinia } from './stores/pinia'
import { useWorkspaceStore } from './stores/workspace'

export function createHaxjobsRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/',
        name: 'workspace',
        component: WorkspaceView,
      },
      {
        path: '/review',
        name: 'review',
        component: ReviewView,
      },
      {
        path: '/drafts',
        name: 'drafts',
        component: DraftsView,
      },
    ],
  })

  router.beforeEach((to) => {
    const store = useWorkspaceStore(pinia)
    if ((to.name === 'review' || to.name === 'drafts') && !store.hasAnalysis) {
      return { name: 'workspace' }
    }
    if (to.name === 'drafts' && !store.canAccessDrafts) {
      return { name: 'review', query: { panel: 'questions' } }
    }
    return true
  })

  return router
}
