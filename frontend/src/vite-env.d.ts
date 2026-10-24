/// <reference types="vite/client" />

// Vite 环境类型声明：资源导入等；*.vue 由 vue-tsc 内置支持
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
