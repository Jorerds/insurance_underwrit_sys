<script setup lang="ts">
// 核保规则配置（admin）：条件表单化维护，支持启停
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { fetchAdminProducts, fetchAdminQuestions, type AdminProduct } from '@/api/application'
import {
  createRule,
  fetchRules,
  updateRule,
  type RuleAction,
  type UnderwritingRule,
} from '@/api/underwriting'
import { RULE_ACTION_NAMES } from '@/utils/dict'

const products = ref<AdminProduct[]>([])
const rows = ref<UnderwritingRule[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const editing = ref<UnderwritingRule | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)

// 对话框中按所选险种加载其题目，供风险题条件多选
const productQuestions = ref<{ id: number; content: string }[]>([])

const form = reactive({
  product_id: null as number | null,
  rule_name: '',
  action: 'EXTRA' as RuleAction,
  question_ids: [] as number[],
  disease_keywords: '',
  family_keywords: '',
  min_age: null as number | null,
  max_age: null as number | null,
  min_amount: '',
  extra_rate: '',
  exclusion_desc: '',
  postpone_months: null as number | null,
  status: 1,
})

const ACTION_OPTIONS = Object.entries(RULE_ACTION_NAMES).map(([value, label]) => ({ value, label }))

const rules: FormRules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
}

// 适用险种下拉选项（含通用）
const productOptions = computed(() => [
  { id: null, name: '全部险种（通用）' },
  ...products.value.map((p) => ({ id: p.id, name: p.name })),
])

/** 险种名展示（含通用规则） */
function productName(productId: number | null): string {
  if (productId === null) return '全部险种'
  return products.value.find((p) => p.id === productId)?.name ?? `险种#${productId}`
}

/** 条件摘要文本 */
function conditionText(row: UnderwritingRule): string {
  const c = row.condition
  const parts: string[] = []
  if (c.question_ids?.length) parts.push(`风险题×${c.question_ids.length}`)
  if (c.disease_keywords?.length) parts.push(`病史含：${c.disease_keywords.join('/')}`)
  if (c.family_keywords?.length) parts.push(`家族病史含：${c.family_keywords.join('/')}`)
  if (c.min_age !== null && c.min_age !== undefined) parts.push(`年龄≥${c.min_age}`)
  if (c.max_age !== null && c.max_age !== undefined) parts.push(`年龄≤${c.max_age}`)
  if (c.min_amount) parts.push(`保额≥${c.min_amount}`)
  return parts.length ? parts.join('；') : '（无条件，不触发）'
}

/** 动作参数摘要 */
function actionText(row: UnderwritingRule): string {
  if (row.action === 'EXTRA') return `加费 ${row.extra_rate}%`
  if (row.action === 'EXCLUSION') return row.exclusion_desc ?? ''
  if (row.action === 'POSTPONE') return `延期 ${row.postpone_months} 个月`
  return ''
}

async function load() {
  loading.value = true
  try {
    const [p, r] = await Promise.all([fetchAdminProducts(), fetchRules()])
    products.value = p
    rows.value = r
  } finally {
    loading.value = false
  }
}
onMounted(load)

/** 对话框中险种变化时重新加载题目选项 */
async function onFormProductChange() {
  form.question_ids = []
  productQuestions.value = form.product_id
    ? (await fetchAdminQuestions(form.product_id)).map((q) => ({ id: q.id, content: q.content }))
    : []
}

/** 打开新增/编辑对话框 */
async function openDialog(row: UnderwritingRule | null) {
  editing.value = row
  form.product_id = row?.product_id ?? null
  form.rule_name = row?.rule_name ?? ''
  form.action = (row?.action as RuleAction) ?? 'EXTRA'
  form.question_ids = row ? [...(row.condition.question_ids ?? [])] : []
  form.disease_keywords = row?.condition.disease_keywords?.join(',') ?? ''
  form.family_keywords = row?.condition.family_keywords?.join(',') ?? ''
  form.min_age = row?.condition.min_age ?? null
  form.max_age = row?.condition.max_age ?? null
  form.min_amount = row?.condition.min_amount ?? ''
  form.extra_rate = row?.extra_rate ?? ''
  form.exclusion_desc = row?.exclusion_desc ?? ''
  form.postpone_months = row?.postpone_months ?? null
  form.status = row?.status ?? 1
  dialogVisible.value = true
  await onFormProductChange()
  if (row) form.question_ids = [...(row.condition.question_ids ?? [])]
}

/** 关键词逗号分隔转数组（去空白） */
function splitKeywords(text: string): string[] {
  return text.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
}

/** 保存规则 */
async function onSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    const body = {
      product_id: form.product_id,
      rule_name: form.rule_name,
      action: form.action,
      condition: {
        question_ids: form.question_ids,
        disease_keywords: splitKeywords(form.disease_keywords),
        family_keywords: splitKeywords(form.family_keywords),
        min_age: form.min_age,
        max_age: form.max_age,
        min_amount: form.min_amount || null,
      },
      extra_rate: form.action === 'EXTRA' ? form.extra_rate : null,
      exclusion_desc: form.action === 'EXCLUSION' ? form.exclusion_desc : null,
      postpone_months: form.action === 'POSTPONE' ? form.postpone_months : null,
      status: form.status,
    }
    if (editing.value) {
      await updateRule(editing.value.id, body)
    } else {
      await createRule(body)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

/** 启停切换 */
async function onToggle(row: UnderwritingRule, status: number) {
  await updateRule(row.id, {
    product_id: row.product_id,
    rule_name: row.rule_name,
    action: row.action as RuleAction,
    condition: { ...row.condition },
    extra_rate: row.extra_rate,
    exclusion_desc: row.exclusion_desc,
    postpone_months: row.postpone_months,
    status,
  })
  ElMessage.success(status === 1 ? '已启用' : '已停用')
  await load()
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="flex justify-between items-center">
        <span>核保规则配置</span>
        <el-button type="primary" @click="openDialog(null)">新增规则</el-button>
      </div>
    </template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="rule_name" label="规则名称" min-width="160" />
      <el-table-column label="适用险种" width="130">
        <template #default="{ row }">{{ productName(row.product_id) }}</template>
      </el-table-column>
      <el-table-column label="触发条件" min-width="240">
        <template #default="{ row }">{{ conditionText(row) }}</template>
      </el-table-column>
      <el-table-column label="动作" width="120">
        <template #default="{ row }">{{ RULE_ACTION_NAMES[row.action] ?? row.action }}</template>
      </el-table-column>
      <el-table-column label="动作参数" min-width="150">
        <template #default="{ row }">{{ actionText(row) || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="row.status === 1" link type="warning" @click="onToggle(row, 0)">
            停用
          </el-button>
          <el-button v-else link type="success" @click="onToggle(row, 1)">启用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑规则' : '新增规则'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="规则名称" prop="rule_name">
          <el-input v-model="form.rule_name" placeholder="如：高血压加费" />
        </el-form-item>
        <el-form-item label="适用险种">
          <el-select v-model="form.product_id" class="w-full" @change="onFormProductChange">
            <el-option v-for="p in productOptions" :key="String(p.id)" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作">
          <el-select v-model="form.action" class="w-full">
            <el-option v-for="o in ACTION_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.action === 'EXTRA'" label="加费比例（%）">
          <el-input v-model="form.extra_rate" class="w-40" placeholder="如 25.00" />
        </el-form-item>
        <el-form-item v-if="form.action === 'EXCLUSION'" label="除外责任">
          <el-input v-model="form.exclusion_desc" type="textarea" :rows="2" placeholder="如：除外甲状腺疾病及其并发症责任" />
        </el-form-item>
        <el-form-item v-if="form.action === 'POSTPONE'" label="延期月数">
          <el-input-number v-model="form.postpone_months" :min="1" :max="120" />
        </el-form-item>

        <el-divider content-position="left">触发条件（任一命中即触发）</el-divider>
        <el-form-item label="风险题">
          <el-select v-model="form.question_ids" multiple class="w-full" placeholder="选择健康告知风险题（该题答'是'即命中）">
            <el-option v-for="q in productQuestions" :key="q.id" :label="q.content" :value="q.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="既往病史关键词">
          <el-input v-model="form.disease_keywords" placeholder="多个关键词用逗号分隔，如：糖尿病,高血压" />
        </el-form-item>
        <el-form-item label="家族病史关键词">
          <el-input v-model="form.family_keywords" placeholder="多个关键词用逗号分隔，如：癌,心脏病" />
        </el-form-item>
        <el-form-item label="年龄范围">
          <el-input-number v-model="form.min_age" :min="0" :max="120" placeholder="下限" />
          <span class="mx-2">至</span>
          <el-input-number v-model="form.max_age" :min="0" :max="120" placeholder="上限" />
        </el-form-item>
        <el-form-item label="保额下限（元）">
          <el-input v-model="form.min_amount" class="w-48" placeholder="如 2000000.00" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
