// 用户状态管理：令牌、当前用户信息、登录/登出
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { request } from '@/api'

/** 当前登录用户信息 */
export interface UserProfile {
  id: number
  username: string
  real_name: string
  role: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') ?? '')
  const profile = ref<UserProfile | null>(null)

  /** 登录：成功后保存令牌并拉取用户信息 */
  async function login(username: string, password: string) {
    const data = await request<{ token: string; role: string }>({
      method: 'POST',
      url: '/auth/login',
      data: { username, password },
    })
    token.value = data.token
    localStorage.setItem('token', data.token)
    await fetchProfile()
  }

  /** 拉取当前用户信息；令牌失效时由拦截器统一处理跳转 */
  async function fetchProfile() {
    const data = await request<UserProfile>({ method: 'GET', url: '/auth/me' })
    profile.value = data
  }

  /** 登出：清理本地登录态 */
  function logout() {
    token.value = ''
    profile.value = null
    localStorage.removeItem('token')
  }

  return { token, profile, login, fetchProfile, logout }
})
