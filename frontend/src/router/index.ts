// 路由配置：登录页 + 受保护的主布局，路由守卫控制未登录与角色访问
import { createRouter, createWebHistory } from 'vue-router'

import { useUserStore } from '@/stores/user'
import AppLayout from '@/views/layout/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      // 主布局下均为需要登录的页面
      path: '/',
      component: AppLayout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '工作台' },
        },
        {
          path: 'apply',
          name: 'apply',
          component: () => import('@/views/ApplyView.vue'),
          meta: { title: '投保申请', roles: ['customer'] },
        },
        {
          path: 'my-applications',
          name: 'my-applications',
          component: () => import('@/views/MyApplicationsView.vue'),
          meta: { title: '我的申请', roles: ['customer'] },
        },
        {
          path: 'my-applications/:id',
          name: 'application-detail',
          component: () => import('@/views/ApplicationDetailView.vue'),
          meta: { title: '申请详情', roles: ['customer'] },
        },
        {
          path: 'admin/products',
          name: 'admin-products',
          component: () => import('@/views/admin/AdminProductsView.vue'),
          meta: { title: '险种管理', roles: ['admin'] },
        },
        {
          path: 'admin/rules',
          name: 'admin-rules',
          component: () => import('@/views/admin/AdminRulesView.vue'),
          meta: { title: '核保规则', roles: ['admin'] },
        },
        {
          path: 'underwriting/tasks',
          name: 'underwriting-tasks',
          component: () => import('@/views/underwriting/UnderwriterTasksView.vue'),
          meta: { title: '核保待办', roles: ['underwriter', 'supervisor'] },
        },
        {
          path: 'underwriting/tasks/:id',
          name: 'underwriting-task-detail',
          component: () => import('@/views/underwriting/TaskDetailView.vue'),
          meta: { title: '案件处理', roles: ['underwriter', 'supervisor'] },
        },
        {
          path: 'underwriting/reviews',
          name: 'underwriting-reviews',
          component: () => import('@/views/underwriting/SupervisorReviewsView.vue'),
          meta: { title: '复核中心', roles: ['supervisor'] },
        },
        {
          path: 'underwriting/reconsiderations',
          name: 'underwriting-reconsiderations',
          component: () => import('@/views/underwriting/SupervisorReconsiderView.vue'),
          meta: { title: '复议处理', roles: ['supervisor'] },
        },
        {
          path: 'stats',
          name: 'stats',
          component: () => import('@/views/stats/StatsView.vue'),
          meta: { title: '统计看板', roles: ['underwriter', 'supervisor'] },
        },
        {
          path: 'exams/entry',
          name: 'exam-entry',
          component: () => import('@/views/exam/ExamEntryView.vue'),
          meta: { title: '体检录入', roles: ['exam_center'] },
        },
        {
          path: 'admin/centers',
          name: 'admin-centers',
          component: () => import('@/views/admin/AdminCentersView.vue'),
          meta: { title: '体检机构', roles: ['admin'] },
        },
        {
          path: 'admin/exam-items',
          name: 'admin-exam-items',
          component: () => import('@/views/admin/AdminExamItemsView.vue'),
          meta: { title: '体检项目', roles: ['admin'] },
        },
        {
          path: 'admin/products/:id/questions',
          name: 'admin-questions',
          component: () => import('@/views/admin/AdminQuestionsView.vue'),
          meta: { title: '问卷配置', roles: ['admin'] },
        },
      ],
    },
  ],
})

// 全局守卫：未携带令牌访问受保护页面时跳转登录页；按 meta.roles 校验页面访问权限
router.beforeEach(async (to) => {
  const hasToken = Boolean(localStorage.getItem('token'))
  if (to.path === '/login') {
    return hasToken ? { path: '/' } : true
  }
  if (!hasToken) {
    return { path: '/login' }
  }
  const userStore = useUserStore()
  if (!userStore.profile) {
    // 刷新页面后恢复用户信息；拉取失败（令牌失效）由拦截器统一跳登录
    await userStore.fetchProfile().catch(() => undefined)
  }
  const roles = to.meta.roles as string[] | undefined
  if (roles && userStore.profile && !roles.includes(userStore.profile.role)) {
    return { path: '/dashboard' }
  }
  return true
})

export default router
