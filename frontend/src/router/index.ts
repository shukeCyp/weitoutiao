import { createRouter, createWebHashHistory } from 'vue-router'

import AiLabView from '../views/AiLabView.vue'
import ArticleMonitoringView from '../views/ArticleMonitoringView.vue'
import ArticlesView from '../views/ArticlesView.vue'
import BenchmarkAccountsView from '../views/BenchmarkAccountsView.vue'
import HomeView from '../views/HomeView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/benchmark-accounts',
      name: 'benchmark-accounts',
      component: BenchmarkAccountsView,
    },
    {
      path: '/article-monitoring',
      name: 'article-monitoring',
      component: ArticleMonitoringView,
    },
    {
      path: '/articles',
      name: 'articles',
      component: ArticlesView,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
    {
      path: '/ai-lab',
      name: 'ai-lab',
      component: AiLabView,
    },
  ],
})

export default router
