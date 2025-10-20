import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
// import API wrapper to patch fetch and handle token storage globally
import './api'

createApp(App).mount('#app')
