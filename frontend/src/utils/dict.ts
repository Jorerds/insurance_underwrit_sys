// 业务字典：状态与角色的中文映射，供列表与详情展示
import type { TagProps } from 'element-plus'

/** 申请单状态中文名 */
export const APP_STATUS_NAMES: Record<string, string> = {
  PENDING: '待核保',
  AUTO_UNDERWRITING: '智能核保中',
  EXAM_REQUIRED: '待体检',
  MANUAL_REQUIRED: '待人工核保',
  REVIEWING: '复核中',
  DECIDED: '已出结论',
  RECONSIDERING: '复议中',
  RECONSIDERED: '复议完成',
}

/** 申请单状态对应的标签颜色 */
export const APP_STATUS_TYPES: Record<string, TagProps['type']> = {
  PENDING: 'info',
  AUTO_UNDERWRITING: 'warning',
  EXAM_REQUIRED: 'warning',
  MANUAL_REQUIRED: 'warning',
  REVIEWING: 'warning',
  DECIDED: 'success',
  RECONSIDERING: 'warning',
  RECONSIDERED: 'success',
}

/** 问卷答案中文展示 */
export function answerText(answer: string): string {
  if (answer === 'yes') return '是'
  if (answer === 'no') return '否'
  return answer
}

/** 核保结论类型中文名 */
export const RESULT_NAMES: Record<string, string> = {
  STANDARD: '标体承保',
  EXTRA: '加费承保',
  EXCLUSION: '除外承保',
  POSTPONE: '延期',
  DECLINE: '拒保',
}

/** 结论类型标签颜色 */
export const RESULT_TYPES: Record<string, TagProps['type']> = {
  STANDARD: 'success',
  EXTRA: 'warning',
  EXCLUSION: 'warning',
  POSTPONE: 'danger',
  DECLINE: 'danger',
}

/** 规则动作中文名 */
export const RULE_ACTION_NAMES: Record<string, string> = {
  ...RESULT_NAMES,
  MANUAL: '转人工核保',
  EXAM: '要求体检',
}

/** 体检单状态中文名 */
export const EXAM_STATUS_NAMES: Record<string, string> = {
  PENDING: '待体检',
  RESULT_ENTERED: '结果已录入',
  DONE: '评估完成',
}
