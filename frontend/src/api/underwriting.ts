// 核保规则相关接口类型与请求函数
import { request } from '@/api'

/** 规则触发条件 */
export interface RuleCondition {
  question_ids: number[]
  disease_keywords: string[]
  family_keywords: string[]
  min_age: number | null
  max_age: number | null
  min_amount: string | null
}

/** 核保规则 */
export interface UnderwritingRule {
  id: number
  product_id: number | null
  rule_name: string
  condition: RuleCondition
  action: string
  extra_rate: string | null
  exclusion_desc: string | null
  postpone_months: number | null
  status: number
}

export type RuleAction = 'STANDARD' | 'EXTRA' | 'EXCLUSION' | 'POSTPONE' | 'DECLINE' | 'MANUAL' | 'EXAM'

/** 规则创建/编辑体 */
export interface RuleBody {
  product_id: number | null
  rule_name: string
  condition: RuleCondition
  action: RuleAction
  extra_rate: string | null
  exclusion_desc: string | null
  postpone_months: number | null
  status: number
}

export function fetchRules(productId?: number) {
  const url = productId ? `/admin/rules?product_id=${productId}` : '/admin/rules'
  return request<UnderwritingRule[]>({ method: 'GET', url })
}

export function createRule(data: RuleBody) {
  return request<{ id: number }>({ method: 'POST', url: '/admin/rules', data })
}

export function updateRule(id: number, data: RuleBody) {
  return request<{ id: number }>({ method: 'PUT', url: `/admin/rules/${id}`, data })
}
