import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
// Marca lo que escribe datos: en solo lectura se oculta (ADR-055, html.solo-lectura en App.vue)
app.directive('escribe', { mounted: (el) => el.setAttribute('data-escribe', '') })

app.mount('#app')
