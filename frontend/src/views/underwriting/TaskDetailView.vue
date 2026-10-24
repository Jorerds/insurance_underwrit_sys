<script setup lang="ts">
// 核保案件详情：投保资料 + 智能核保建议 + 人工结论表单
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { fetchTaskDetail, submitConclusion, type TaskDetail } from '@/api/manual'
import { createExamOrder, fetchExamCenters, fetchExamItems, type ExamCenter, type ExamItem } from '@/api/exam'
import { APP_STATUS_NAMES, APP_STATUS_TYPES, EXAM_STATUS_NAMES, RESULT_NAMES, RULE_ACTION_NAMES, answerText } from '@/utils/dict'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const appId = Number(route.params.id)

const task = ref<TaskDetail | null>(null)
const loading = ref(true)

// 结论表单
const formRef = ref<FormInstance>()
const saving = ref(false)
const form = reactive({
  result_type: 'STANDARD' as string,
  reason: '',
  extra_rate: '',
  exclusion_desc: '',
  postpone_months: null as number | null,
})

const rules: FormRules = {
  reason: [{ required: true, message: '请填写理由说明', trigger: 'blur' }],
}

const RELATION_NAMES: Record<string, string> = { FATHER: '父亲', MOTHER: '母亲', SIBLING: '兄弟姐妹' }

// 仅待人工核保状态且当前用户为核保员时可出具结论
const canDecide = computed(() =>
  task.value?.detail.status === 'MANUAL_REQUIRED' && userStore.profile?.role === 'underwriter')

// 体检单创建（核保员/主管，案件处于待体检或待人工核保时可创建）
const examDialogVisible = ref(false)
const examCenters = ref<ExamCenter[]>([])
const examItems = ref<ExamItem[]>([])
const examSaving = ref(false)
const examForm = reactive({ center_id: null as number | null, item_ids: [] as number[] })
const canCreateExam = computed(() =>
  ['EXAM_REQUIRED', 'MANUAL_REQUIRED'].includes(task.value?.detail.status ?? '') &&
  ['underwriter', 'supervisor'].includes(userStore.profile?.role ?? ''))

async function reload() {
  task.value = await fetchTaskDetail(appId)
}

onMounted(async () => {
  try {
    task.value = await fetchTaskDetail(appId)
  } finally {
    loading.value = false
  }
})

/** 打开创建体检单对话框 */
async function openExamDialog() {
  const [centers, items] = await Promise.all([fetchExamCenters(), fetchExamItems()])
  examCenters.value = centers
  examItems.value = items
  examForm.center_id = null
  examForm.item_ids = []
  examDialogVisible.value = true
}

/** 提交体检单 */
async function onCreateExam() {
  if (!examForm.center_id) {
    ElMessage.warning('请选择体检机构')
    return
  }
  if (!examForm.item_ids.length) {
    ElMessage.warning('请勾选体检项目')
    return
  }
  examSaving.value = true
  try {
    await createExamOrder({
      application_id: appId,
      center_id: examForm.center_id,
      item_ids: examForm.item_ids,
    })
    ElMessage.success('体检单已创建，案件已锁定为待体检')
    examDialogVisible.value = false
    await reload()
  } finally {
    examSaving.value = false
  }
}

/** 提交人工结论 */
async function onSubmit() {
  await formRef.value?.validate()
  saving.value = true
  try {
    await submitConclusion(appId, {
      result_type: form.result_type,
      reason: form.reason,
      extra_rate: form.result_type === 'EXTRA' ? form.extra_rate : null,
      exclusion_desc: form.result_type === 'EXCLUSION' ? form.exclusion_desc : null,
      postpone_months: form.result_type === 'POSTPONE' ? form.postpone_months : null,
    })
    ElMessage.success('结论已提交，等待主管复核')
    router.push('/underwriting/tasks')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-loading="loading">
    <el-card v-if="task">
      <template #header>
        <div class="flex justify-between items-center">
          <span>案件处理（{{ task.detail.app_no }}）</span>
          <el-tag :type="APP_STATUS_TYPES[task.detail.status] ?? 'info'">
            {{ APP_STATUS_NAMES[task.detail.status] ?? task.detail.status }}
          </el-tag>
        </div>
      </template>

      <!-- 体检单 -->
      <template v-if="task.exam_orders?.length">
        <el-divider content-position="left">体检单</el-divider>
        <el-table :data="task.exam_orders" class="mb-6">
          <el-table-column prop="id" label="单号" width="80" />
          <el-table-column prop="center_name" label="体检机构" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">{{ EXAM_STATUS_NAMES[row.status] ?? row.status }}</template>
          </el-table-column>
          <el-table-column label="体检项目与结果" min-width="280">
            <template #default="{ row }">
              <div v-for="i in row.items" :key="i.item_id" class="text-sm">
                {{ i.item_name }}：
                <template v-if="i.result_value">
                  {{ i.result_value }}
                  <el-tag v-if="i.is_abnormal === 1" type="danger" size="small">异常</el-tag>
                </template>
                <span v-else class="text-slate-400">待录入</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="overall_result" label="体检总结论" min-width="180">
            <template #default="{ row }">{{ row.overall_result || '-' }}</template>
          </el-table-column>
        </el-table>
      </template>

      <!-- 智能核保建议 -->
      <template v-if="task.auto_advice?.hits?.length">
        <el-divider content-position="left">智能核保建议（命中规则）</el-divider>
        <el-table :data="task.auto_advice.hits" class="mb-6">
          <el-table-column prop="rule_name" label="规则名称" min-width="160" />
          <el-table-column label="动作" width="120">
            <template #default="{ row }">{{ RULE_ACTION_NAMES[row.action] ?? row.action }}</template>
          </el-table-column>
          <el-table-column prop="matched_by" label="命中依据" min-width="180" />
        </el-table>
      </template>

      <!-- 已有人工结论记录（退回时展示复核意见） -->
      <template v-if="task.latest_manual_result">
        <el-divider content-position="left">上次核保结论</el-divider>
        <el-alert type="warning" :closable="false" class="mb-6">
          <template #title>
            {{ RESULT_NAMES[task.latest_manual_result.result_type] }} —— {{ task.latest_manual_result.reason }}
          </template>
          <template v-if="task.latest_manual_result.review_status === 'RETURNED'">
            主管复核意见：{{ task.latest_manual_result.review_comment }}
          </template>
        </el-alert>
      </template>

      <el-descriptions title="基本信息" :column="2" border class="mb-6">
        <el-descriptions-item label="客户">{{ task.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="险种">{{ task.detail.product_name }}</el-descriptions-item>
        <el-descriptions-item label="投保人">{{ task.detail.applicant_name }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ task.detail.gender === 'M' ? '男' : '女' }}</el-descriptions-item>
        <el-descriptions-item label="出生日期">{{ task.detail.birth_date }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ task.detail.phone }}</el-descriptions-item>
        <el-descriptions-item label="证件号码">{{ task.detail.id_card_no }}</el-descriptions-item>
        <el-descriptions-item label="职业">{{ task.detail.occupation || '-' }}</el-descriptions-item>
        <el-descriptions-item label="保额（元）">{{ Number(task.detail.coverage_amount).toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="保障期限">{{ task.detail.coverage_period }}</el-descriptions-item>
        <el-descriptions-item label="缴费方式">{{ task.detail.pay_method }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">健康告知答卷</el-divider>
      <el-table :data="task.detail.answers" class="mb-6">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="content" label="题目" min-width="280" />
        <el-table-column label="回答" width="80">
          <template #default="{ row }">{{ answerText(row.answer) }}</template>
        </el-table-column>
        <el-table-column prop="detail" label="详细说明" min-width="200">
          <template #default="{ row }">{{ row.detail || '-' }}</template>
        </el-table-column>
      </el-table>

      <el-divider content-position="left">既往病史</el-divider>
      <el-table :data="task.detail.medical_histories" class="mb-6">
        <el-table-column prop="disease_name" label="疾病名称" />
        <el-table-column prop="diagnosed_at" label="诊断时间" width="130" />
        <el-table-column prop="treatment" label="治疗情况">
          <template #default="{ row }">{{ row.treatment || '-' }}</template>
        </el-table-column>
        <template #empty><el-empty description="无既往病史" :image-size="60" /></template>
      </el-table>

      <el-divider content-position="left">家族病史</el-divider>
      <el-table :data="task.detail.family_histories" class="mb-6">
        <el-table-column label="亲属关系" width="110">
          <template #default="{ row }">{{ RELATION_NAMES[row.relation] ?? row.relation }}</template>
        </el-table-column>
        <el-table-column prop="disease_name" label="疾病名称" />
        <el-table-column prop="diagnosed_at" label="确诊时间" width="130" />
        <el-table-column prop="treatment" label="治疗情况">
          <template #default="{ row }">{{ row.treatment || '-' }}</template>
        </el-table-column>
        <template #empty><el-empty description="无家族病史" :image-size="60" /></template>
      </el-table>

      <!-- 人工结论表单 -->
      <template v-if="canDecide">        <el-divider content-position="left">出具核保结论</el-divider>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="max-w-2xl">
          <el-form-item label="结论类型" required>
            <el-radio-group v-model="form.result_type">
              <el-radio-button v-for="(name, key) in RESULT_NAMES" :key="key" :value="key">
                {{ name }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.result_type === 'EXTRA'" label="加费比例（%）" required>
            <el-input v-model="form.extra_rate" class="w-40" placeholder="如 25.00" />
          </el-form-item>
          <el-form-item v-if="form.result_type === 'EXCLUSION'" label="除外责任" required>
            <el-input v-model="form.exclusion_desc" type="textarea" :rows="2" placeholder="如：除外甲状腺疾病及其并发症责任" />
          </el-form-item>
          <el-form-item v-if="form.result_type === 'POSTPONE'" label="延期月数" required>
            <el-input-number v-model="form.postpone_months" :min="1" :max="120" />
          </el-form-item>
          <el-form-item label="理由说明" prop="reason">
            <el-input v-model="form.reason" type="textarea" :rows="3" placeholder="请说明核保依据" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="onSubmit">提交结论（进入复核）</el-button>
          </el-form-item>
        </el-form>
      </template>
      <!-- 创建体检单入口（放在结论表单之后） -->
      <div v-if="canCreateExam" class="mt-2">
        <el-divider content-position="left">体检安排</el-divider>
        <el-button type="primary" plain @click="openExamDialog">创建体检单</el-button>
      </div>
      <!-- 待人工核保但当前用户不是核保员（如主管查看）：明确提示，避免误以为按钮缺失 -->
      <el-result v-if="task.detail.status === 'MANUAL_REQUIRED' && userStore.profile?.role !== 'underwriter'"
        icon="info" title="该案件待人工核保" sub-title="请由核保员账号登录并出具结论；主管请在复核中心处理复核" />
      <el-result v-else-if="task.detail.status === 'REVIEWING'"
        icon="info" title="该案件正在复核中" sub-title="请等待核保主管复核" />
    </el-card>

    <!-- 创建体检单对话框 -->
    <el-dialog v-model="examDialogVisible" title="创建体检单" width="560px">
      <el-form label-width="90px">
        <el-form-item label="体检机构" required>
          <el-select v-model="examForm.center_id" class="w-full" placeholder="选择体检机构">
            <el-option v-for="c in examCenters" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="体检项目" required>
          <el-checkbox-group v-model="examForm.item_ids">
            <el-checkbox v-for="i in examItems" :key="i.id" :value="i.id" class="!block">
              {{ i.name }}<span v-if="i.ref_range" class="text-slate-400 text-xs">（参考：{{ i.ref_range }}）</span>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="examDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="examSaving" @click="onCreateExam">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
