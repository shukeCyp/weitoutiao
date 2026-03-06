import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import './styles/base.css'
import './styles/linear.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const themeStore = useThemeStore()
void themeStore.initialize()

app.mount('#app')
