import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import JobsView from '../views/JobsView.vue'
import ProfilesView from '../views/ProfilesView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: HomeView,
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: JobsView,
    },
    {
      path: '/profiles',
      name: 'profiles',
      component: ProfilesView,
    },
  ],
})

export default router
