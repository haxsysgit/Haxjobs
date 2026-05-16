import { createRouter, createWebHistory } from "vue-router";

import DraftsPage from "./pages/DraftsPage.vue";
import ReviewPage from "./pages/ReviewPage.vue";
import WorkspacePage from "./pages/WorkspacePage.vue";
import { canAccessOutputs, hasAnalysis } from "./state/app-state";

export function createHaxjobsRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: "/",
        name: "workspace",
        component: WorkspacePage
      },
      {
        path: "/review",
        name: "review",
        component: ReviewPage
      },
      {
        path: "/drafts",
        name: "drafts",
        component: DraftsPage
      }
    ]
  });

  router.beforeEach((to) => {
    if ((to.name === "review" || to.name === "drafts") && !hasAnalysis()) {
      return { name: "workspace" };
    }
    if (to.name === "drafts") {
      if (!hasAnalysis()) {
        return { name: "workspace" };
      }
      if (!canAccessOutputs()) {
        return { name: "review", query: { panel: "questions" } };
      }
    }
    return true;
  });

  return router;
}
