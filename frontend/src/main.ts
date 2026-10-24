/// <reference types="vite/client" />

// 应用入口：装配 Pinia、路由、Element Plus（中文语言包）并挂载根组件
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
// 统一使用中文语言包，保证组件内置提示（分页、日期等）为中文
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
