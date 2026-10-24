// 投保申请相关接口类型与请求函数
import { request } from '@/api'

/** 问卷题目（客户视图） */
export interface Question {
  id: number
  content: string
  sort: number
  is_risk: number
  answer_type: string
  is_required: number
}

/** 可投保险种（含启用题目） */
export interface Product {
  id: number
  code: string
  name: string
  description: string | null
  questions: Question[]
}

/** 单题答卷 */
export interface AnswerItem {
  question_id: number
  answer: string
  detail?: string | null
}

/** 投保申请提交体 */
export interface ApplicationCreate {
  product_id: number
  applicant_name: string
  gender: 'M' | 'F'
  birth_date: string
  id_card_no: string
  phone: string
  occupation?: string | null
  coverage_amount: string
  coverage_period: string
  pay_method: string
  answers: AnswerItem[]
  medical_histories: { disease_name: string; diagnosed_at: string; treatment?: string | null }[]
  family_histories: { relation: string; disease_name: string; diagnosed_at: string; treatment?: string | null }[]
}

/** 申请列表项 */
export interface ApplicationListItem {
  id: number
  app_no: string
  product_name: string
  applicant_name: string
  gender: string
  coverage_amount: string
  status: string
  created_at: string
}

/** 核保结论（客户可见部分） */
export interface UnderwritingResult {
  result_type: string
  reason: string
  extra_rate: string | null
  exclusion_desc: string | null
  postpone_months: number | null
  source: string
  decided_at: string
  is_final: number
}

/** 复议记录（客户视角） */
export interface Reconsideration {
  status: 'PENDING' | 'DONE'
  reason: string
  comment: string | null
  handled_at: string | null
  final_result_type: string | null
}

/** 申请详情 */
export interface ApplicationDetail extends ApplicationListItem {
  product_id: number
  birth_date: string
  id_card_no: string
  phone: string
  occupation: string | null
  coverage_period: string
  pay_method: string
  answers: { question_id: number; content: string; answer_type: string; answer: string; detail: string | null }[]
  medical_histories: { disease_name: string; diagnosed_at: string; treatment: string | null }[]
  family_histories: { relation: string; disease_name: string; diagnosed_at: string; treatment: string | null }[]
  /** 已生效的核保结论，未出具时为空 */
  result: UnderwritingResult | null
  /** 复议记录，未发起时为空 */
  reconsideration: Reconsideration | null
}

/** 险种与问卷（管理视角） */
export interface AdminProduct {
  id: number
  code: string
  name: string
  description: string | null
  status: number
}

export interface AdminQuestion {
  id: number
  content: string
  sort: number
  is_risk: number
  answer_type: string
  is_required: number
  status: number
}

/** 获取可投保险种列表（客户） */
export function fetchProducts() {
  return request<Product[]>({ method: 'GET', url: '/products' })
}

/** 提交投保申请 */
export function createApplication(data: ApplicationCreate) {
  return request<{ id: number; app_no: string }>({ method: 'POST', url: '/applications', data })
}

/** 我的申请列表 */
export function fetchMyApplications() {
  return request<ApplicationListItem[]>({ method: 'GET', url: '/applications' })
}

/** 申请详情 */
export function fetchApplicationDetail(id: number) {
  return request<ApplicationDetail>({ method: 'GET', url: `/applications/${id}` })
}

// ---- 管理端 ----

export function fetchAdminProducts() {
  return request<AdminProduct[]>({ method: 'GET', url: '/admin/products' })
}

export function createAdminProduct(data: Omit<AdminProduct, 'id'>) {
  return request<{ id: number }>({ method: 'POST', url: '/admin/products', data })
}

export function updateAdminProduct(id: number, data: Omit<AdminProduct, 'id'>) {
  return request<{ id: number }>({ method: 'PUT', url: `/admin/products/${id}`, data })
}

export function fetchAdminQuestions(productId: number) {
  return request<AdminQuestion[]>({ method: 'GET', url: `/admin/products/${productId}/questions` })
}

export function createAdminQuestion(productId: number, data: Omit<AdminQuestion, 'id'>) {
  return request<{ id: number }>({ method: 'POST', url: `/admin/products/${productId}/questions`, data })
}

export function updateAdminQuestion(id: number, data: Omit<AdminQuestion, 'id'>) {
  return request<{ id: number }>({ method: 'PUT', url: `/admin/questions/${id}`, data })
}
