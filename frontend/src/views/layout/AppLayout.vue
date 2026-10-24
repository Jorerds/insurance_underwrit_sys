<script setup lang="ts">
// 主布局：侧边栏（按角色渲染菜单）+ 顶栏 + 内容区
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 角色中文名映射
const ROLE_NAMES: Record<string, string> = {
  customer: '客户',
  underwriter: '核保员',
  exam_center: '体检机构',
  supervisor: '核保主管',
  admin: '管理员',
}

const roleName = computed(() => ROLE_NAMES[userStore.profile?.role ?? ''] ?? userStore.profile?.role)

// 当前角色可见菜单
const menus = computed(() => {
  const role = userStore.profile?.role
  const base = [{ title: '工作台', path: '/dashboard' }]
  if (role === 'customer') {
    return [...base, { title: '投保申请', path: '/apply' }, { title: '我的申请', path: '/my-applications' }]
  }
  if (role === 'admin') {
    return [...base,
      { title: '险种管理', path: '/admin/products' },
      { title: '核保规则', path: '/admin/rules' },
      { title: '体检机构', path: '/admin/centers' },
      { title: '体检项目', path: '/admin/exam-items' }]
  }
  // underwriter / exam_center / supervisor：业务页随后续里程碑开放
  if (role === 'underwriter') {
    return [...base,
      { title: '核保待办', path: '/underwriting/tasks' },
      { title: '统计看板', path: '/stats' }]
  }
  if (role === 'supervisor') {
    return [...base,
      { title: '核保待办', path: '/underwriting/tasks' },
      { title: '复核中心', path: '/underwriting/reviews' },
      { title: '复议处理', path: '/underwriting/reconsiderations' },
      { title: '统计看板', path: '/stats' }]
  }
  if (role === 'exam_center') {
    return [...base, { title: '体检录入', path: '/exams/entry' }]
  }
  return base
})

onMounted(() => {
  // 刷新页面后重新拉取用户信息（token 仍有效时）
  if (!userStore.profile) {
    userStore.fetchProfile().catch(() => {
      /* 401 由拦截器统一跳登录 */
    })
  }
})

/** 退出登录并回到登录页 */
function onLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="min-h-screen">
    <el-aside width="220px" class="bg-slate-800">
      <div class="h-14 flex items-center justify-center text-white font-bold">
        医疗保险核保系统
      </div>
      <el-menu router background-color="#1e293b" text-color="#cbd5e1" active-text-color="#ffffff"
        :default-active="$route.path">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">{{ m.title }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="flex items-center justify-between border-b bg-white">
        <span class="text-slate-600">{{ $route.meta.title ?? '' }}</span>
        <div class="flex items-center gap-4">
          <span class="text-sm text-slate-500">
            {{ userStore.profile?.real_name }}（{{ roleName }}）
          </span>
          <el-button size="small" @click="onLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="bg-slate-50">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
