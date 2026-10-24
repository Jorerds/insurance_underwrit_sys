// 统计看板接口类型与请求函数
import { request } from '@/api'

/** 看板汇总 */
export interface StatsSummary {
  total: number
  passed: number
  pass_rate: number
  by_result: Record<string, number>
}

/** 按险种统计 */
export interface ByProduct {
  product_id: number
  product_name: string
  total: number
  passed: number
  pass_rate: number
  results: Record<string, number>
}

/** 按年龄段统计 */
export interface ByAge {
  age_range: string
  total: number
  passed: number
  pass_rate: number
}

/** 按结论统计 */
export interface ByResult {
  result_type: string
  count: number
  ratio: number
}

/** 明细行 */
export interface StatsDetailRow {
  app_no: string
  product_name: string
  applicant_name: string
  age: number
  result_type: string
  source: string
  decided_at: string
}

/** 看板完整数据 */
export interface Dashboard {
  summary: StatsSummary
  by_product: ByProduct[]
  by_age: ByAge[]
  by_result: ByResult[]
  detail: StatsDetailRow[]
}

export function fetchDashboard(dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('from', dateFrom)
  if (dateTo) params.set('to', dateTo)
  const qs = params.toString()
  return request<Dashboard>({ method: 'GET', url: `/stats/dashboard${qs ? `?${qs}` : ''}` })
}

/** 导出相对路径（baseURL 已含 /api/v1，切勿再带前缀，否则会拼出双前缀 404） */
export function exportUrl(format: 'xlsx' | 'csv', dateFrom?: string, dateTo?: string): string {
  const params = new URLSearchParams({ format })
  if (dateFrom) params.set('from', dateFrom)
  if (dateTo) params.set('to', dateTo)
  return `/stats/export?${params.toString()}`
}
