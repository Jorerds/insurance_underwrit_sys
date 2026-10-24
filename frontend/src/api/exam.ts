// 体检管理相关接口类型与请求函数
import { request } from '@/api'

/** 体检机构 */
export interface ExamCenter {
  id: number
  name: string
  contact_phone: string | null
  address: string | null
  status: number
}

/** 体检项目 */
export interface ExamItem {
  id: number
  name: string
  unit: string | null
  ref_range: string | null
  sort: number
  status: number
}

/** 体检单项结果 */
export interface ExamItemResult {
  item_id: number
  item_name: string
  result_value: string | null
  is_abnormal: number | null
  remark: string | null
}

/** 体检单 */
export interface ExamOrder {
  id: number
  application_id: number
  app_no: string
  center_id: number
  center_name: string
  status: string
  overall_result: string | null
  created_at: string
  result_entered_at: string | null
  items: ExamItemResult[]
}

export function fetchExamCenters() {
  return request<ExamCenter[]>({ method: 'GET', url: '/exams/exam-centers' })
}

export function fetchExamItems() {
  return request<ExamItem[]>({ method: 'GET', url: '/exams/exam-items' })
}

export function createExamOrder(data: { application_id: number; center_id: number; item_ids: number[] }) {
  return request<{ id: number }>({ method: 'POST', url: '/exams', data })
}

export function fetchExamOrders(applicationId?: number) {
  const url = applicationId ? `/exams?application_id=${applicationId}` : '/exams'
  return request<ExamOrder[]>({ method: 'GET', url })
}

export function fetchExamOrder(id: number) {
  return request<ExamOrder>({ method: 'GET', url: `/exams/${id}` })
}

export function enterExamResult(orderId: number, data: {
  overall_result: string
  item_results: { item_id: number; result_value: string; is_abnormal: number; remark?: string | null }[]
}) {
  return request<{ id: number }>({ method: 'PUT', url: `/exams/${orderId}/result`, data })
}

// ---- 管理端字典 ----

export function fetchAdminCenters() {
  return request<ExamCenter[]>({ method: 'GET', url: '/admin/centers' })
}

export function createAdminCenter(data: Omit<ExamCenter, 'id'>) {
  return request<{ id: number }>({ method: 'POST', url: '/admin/centers', data })
}

export function updateAdminCenter(id: number, data: Omit<ExamCenter, 'id'>) {
  return request<{ id: number }>({ method: 'PUT', url: `/admin/centers/${id}`, data })
}

export function fetchAdminExamItems() {
  return request<ExamItem[]>({ method: 'GET', url: '/admin/exam-items' })
}

export function createAdminExamItem(data: Omit<ExamItem, 'id'>) {
  return request<{ id: number }>({ method: 'POST', url: '/admin/exam-items', data })
}

export function updateAdminExamItem(id: number, data: Omit<ExamItem, 'id'>) {
  return request<{ id: number }>({ method: 'PUT', url: `/admin/exam-items/${id}`, data })
}
