// 复议相关接口类型与请求函数
import { request } from '@/api'

/** 客户视角的复议记录 */
export interface Reconsideration {
  status: 'PENDING' | 'DONE'
  reason: string
  comment: string | null
  handled_at: string | null
  final_result_type: string | null
}

/** 主管处理视角的复议列表项 */
export interface ReconsiderItem {
  id: number
  application_id: number
  app_no: string
  customer_name: string
  result_type: string
  result_reason: string
  reason: string
  original_result_id: number
}

export interface NewResultBody {
  result_type: string
  reason: string
  extra_rate?: string | null
  exclusion_desc?: string | null
  postpone_months?: number | null
}

export function startReconsideration(appId: number, reason: string) {
  return request<{ id: number }>({ method: 'POST', url: `/reconsiderations/by-application/${appId}`, data: { reason } })
}

export function fetchReconsiderations(status = 'PENDING') {
  return request<ReconsiderItem[]>({ method: 'GET', url: `/reconsiderations?status=${status}` })
}

export function handleReconsideration(id: number, data: {
  decision: 'MAINTAIN' | 'CHANGE'
  comment: string
  new_result?: NewResultBody | null
}) {
  return request<{ id: number }>({ method: 'POST', url: `/reconsiderations/${id}/handle`, data })
}
