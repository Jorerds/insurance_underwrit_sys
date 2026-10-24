// HTTP 客户端封装
// 统一注入 JWT、按后端响应格式解包、错误中文提示、401 自动跳登录
import axios, { AxiosError, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

/** 后端统一响应格式 */
export interface ApiResult<T = unknown> {
  code: number
  message: string
  data: T
}

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截：注入 Bearer 令牌
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：解包统一格式；401 自动跳登录；其余错误按状态码给出准确提示
http.interceptors.response.use(
  (resp: AxiosResponse<ApiResult>) => {
    const body = resp.data
    if (body && typeof body.code === 'number') {
      if (body.code !== 0) {
        // 业务错误：中文提示并拒绝，由调用方决定是否捕获
        ElMessage.error(body.message || '请求失败')
        return Promise.reject(new Error(body.message))
      }
      return body as unknown as AxiosResponse
    }
    return resp
  },
  (error: AxiosError<ApiResult>) => {
    const status = error.response?.status
    if (status === 401) {
      localStorage.removeItem('token')
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    } else {
      // 按状态码给出准确提示，避免把权限/服务端错误笼统报成"网络异常"
      const tips: Record<number, string> = {
        403: '无权访问，请确认当前账号角色是否有该操作权限',
        404: '请求的资源不存在',
        422: '请求参数不合法',
        500: '服务器内部错误，请稍后重试',
      }
      ElMessage.error(
        error.response?.data?.message
        ?? (status ? tips[status] ?? `请求失败（错误码 ${status}）` : '网络异常，请检查服务是否已启动')
      )
    }
    // 输出诊断信息，便于在控制台定位真实状态码
    console.error('[请求失败]', error.config?.url, '状态码:', status ?? '无响应', error.message)
    return Promise.reject(error)
  },
)

/** 解包后的便捷请求方法，返回 data 部分 */
export async function request<T = unknown>(...args: Parameters<typeof http.request>): Promise<T> {
  const resp = await http.request(...args)
  return (resp as unknown as ApiResult<T>).data
}

export default http
