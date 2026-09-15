import { createRouter, createWebHistory } from "vue-router";
import { Auth } from "./api";
import LoginView from "./views/LoginView.vue";
import ProblemListView from "./views/ProblemListView.vue";
import ProblemView from "./views/ProblemView.vue";
import SubmissionsView from "./views/SubmissionsView.vue";
import ScoresView from "./views/ScoresView.vue";
import AdminBankRemoteView from "./views/AdminBankRemoteView.vue";
import AdminBankLocalView from "./views/AdminBankLocalView.vue";
import AdminBankFilesView from "./views/AdminBankFilesView.vue";
import AdminProblemStatsView from "./views/AdminProblemStatsView.vue";
import AdminProblemLogView from "./views/AdminProblemLogView.vue";
import AdminUserStatsView from "./views/AdminUserStatsView.vue";
import AdminUserLogView from "./views/AdminUserLogView.vue";
import AdminGuideView from "./views/AdminGuideView.vue";
import DuelView from "./views/DuelView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView, meta: { public: true } },
    { path: "/", component: ProblemListView },
    { path: "/problems/:slug", component: ProblemView },
    { path: "/duel/:code", component: DuelView },
    { path: "/scores", component: ScoresView },
    { path: "/submissions", component: SubmissionsView },
    { path: "/admin", redirect: "/admin/data/problems" },
    { path: "/admin/stats", redirect: "/admin/data/problems" },
    { path: "/admin/stats/submissions", redirect: "/admin/data/users" },
    { path: "/admin/problems", redirect: "/admin/bank/remote" },
    { path: "/admin/data/problems", component: AdminProblemStatsView },
    { path: "/admin/data/problems/:slug", component: AdminProblemLogView },
    { path: "/admin/data/users", component: AdminUserStatsView },
    { path: "/admin/data/users/:userId", component: AdminUserLogView },
    { path: "/admin/bank", redirect: "/admin/bank/remote" },
    { path: "/admin/bank/remote", component: AdminBankRemoteView },
    { path: "/admin/bank/local", component: AdminBankLocalView },
    { path: "/admin/bank/files", component: AdminBankFilesView },
    { path: "/admin/guide", component: AdminGuideView },
  ],
});

router.beforeEach(async (to) => {
  if (to.meta.public) return true;
  try {
    await Auth.me();
    return true;
  } catch {
    return { path: "/login", query: { next: to.fullPath } };
  }
});

export default router;
