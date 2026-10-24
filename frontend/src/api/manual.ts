// 人工核保相关接口类型与请求函数
import { request } from '@/api'
import type { ApplicationDetail } from '@/api/application'
import type { ExamOrder } from '@/api/exam'

/** 核保案件列表项 */
export interface TaskItem {
  id: number
  app_no: string
  product_name: string
  customer_name: string
  applicant_name: string
  gender: string
  coverage_amount: string
  status: string
  created_at: string
}

/** 案件详情 */
export interface TaskDetail {
  detail: ApplicationDetail
  customer_name: string
  /** 智能核保评估快照（转人工/体检时的命中规则） */
  auto_advice: { next_status: string; hits: { rule_id: number; rule_name: string; action: string; matched_by: string }[] } | null
  /** 最新人工结论记录（含复核状态） */
  latest_manual_result: {
    id: number
    result_type: string
    reason: string
    extra_rate: string | null
    exclusion_desc: string | null
    postpone_months: number | null
    source: string
    review_status: string
    review_comment: string | null
    decided_at: string
    is_final: number
  } | null
  /** 关联体检单（含结果） */
  exam_orders: ExamOrder[]
}

/** 复核列表项 */
export interface ReviewItem {
  result_id: number
  app_id: number
  app_no: string
  product_name: string
  customer_name: string
  result_type: string
  reason: string
  underwriter_name: string
  decided_at: string
}

/** 人工结论提交体 */
export interface ConclusionBody {
  result_type: string
  reason: string
  extra_rate?: string | null
  exclusion_desc?: string | null
  postpone_months?: number | null
}

export function fetchTasks(status?: string) {
  const url = status ? `/underwriting/tasks?status=${status}` : '/underwriting/tasks'
  return request<TaskItem[]>({ method: 'GET', url })
}

export function fetchTaskDetail(appId: number) {
  return request<TaskDetail>({ method: 'GET', url: `/underwriting/tasks/${appId}` })
}

export function submitConclusion(appId: number, data: ConclusionBody) {
  return request<{ result_id: number }>({ method: 'POST', url: `/underwriting/tasks/${appId}/conclusion`, data })
}

export function fetchReviews(status = 'PENDING') {
  return request<ReviewItem[]>({ method: 'GET', url: `/underwriting/reviews?status=${status}` })
}

export function approveReview(resultId: number) {
  return request<{ result_id: number }>({ method: 'POST', url: `/underwriting/reviews/${resultId}/approve` })
}

export function returnReview(resultId: number, comment: string) {
  return request<{ result_id: number }>({ method: 'POST', url: `/underwriting/reviews/${resultId}/return`, data: { comment } })
}
