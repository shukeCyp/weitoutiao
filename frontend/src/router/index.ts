import { createRouter, createWebHashHistory } from 'vue-router'

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
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
  ],
})

export default router
