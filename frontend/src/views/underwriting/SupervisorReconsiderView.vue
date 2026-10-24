<script setup lang="ts">
// 复议处理（核保主管）：待处理复议列表，维持或变更结论
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import {
  fetchReconsiderations,
  handleReconsideration,
  type ReconsiderItem,
} from '@/api/reconsider'
import { RESULT_NAMES } from '@/utils/dict'

const router = useRouter()
const rows = ref<ReconsiderItem[]>([])
const loading = ref(true)

// 处理对话框
const handleVisible = ref(false)
const formRef = ref<FormInstance>()
const saving = ref(false)
const current = ref<ReconsiderItem | null>(null)
const form = reactive({
  decision: 'MAINTAIN' as 'MAINTAIN' | 'CHANGE',
  comment: '',
  result_type: 'STANDARD' as string,
  new_reason: '',
  extra_rate: '',
  exclusion_desc: '',
  postpone_months: null as number | null,
})

const rules: FormRules = {
  comment: [{ required: true, message: '请填写复议意见', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    rows.value = await fetchReconsiderations('PENDING')
  } finally {
    loading.value = false
  }
}
onMounted(load)

/** 打开处理对话框 */
function openHandle(row: ReconsiderItem) {
  current.value = row
  form.decision = 'MAINTAIN'
  form.comment = ''
  form.result_type = 'STANDARD'
  form.new_reason = ''
  form.extra_rate = ''
  form.exclusion_desc = ''
  form.postpone_months = null
  handleVisible.value = true
}

/** 提交处理结果 */
async function onHandle() {
  await formRef.value?.validate()
  if (form.decision === 'CHANGE' && !form.new_reason.trim()) {
    ElMessage.warning('变更结论时请填写新结论的理由说明')
    return
  }
  saving.value = true
  try {
    await handleReconsideration(current.value!.id, {
      decision: form.decision,
      comment: form.comment,
      new_result: form.decision === 'CHANGE'
        ? {
            result_type: form.result_type,
            reason: form.new_reason,
            extra_rate: form.result_type === 'EXTRA' ? form.extra_rate : null,
            exclusion_desc: form.result_type === 'EXCLUSION' ? form.exclusion_desc : null,
            postpone_months: form.result_type === 'POSTPONE' ? form.postpone_months : null,
          }
        : null,
    })
    ElMessage.success('复议已处理完成')
    handleVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-card>
    <template #header>复议处理（待处理）</template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="app_no" label="申请单号" width="170" />
      <el-table-column prop="customer_name" label="客户" width="100" />
      <el-table-column label="原结论" width="110">
        <template #default="{ row }">{{ RESULT_NAMES[row.result_type] ?? row.result_type }}</template>
      </el-table-column>
      <el-table-column prop="reason" label="复议理由" min-width="220" show-overflow-tooltip />
      <el-table-column prop="result_reason" label="原结论理由" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/underwriting/tasks/${row.application_id}`)">
            查看案件
          </el-button>
          <el-button link type="warning" @click="openHandle(row)">处理复议</el-button>
        </template>
      </el-table-column>
      <template #empty><el-empty description="暂无待处理复议" /></template>
    </el-table>

    <el-dialog v-model="handleVisible" :title="`处理复议（${current?.app_no}）`" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="复议理由">
          <div class="text-sm text-slate-600">{{ current?.reason }}</div>
        </el-form-item>
        <el-form-item label="复议决定">
          <el-radio-group v-model="form.decision">
            <el-radio-button value="MAINTAIN">维持原结论</el-radio-button>
            <el-radio-button value="CHANGE">变更结论</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="form.decision === 'CHANGE'">
          <el-form-item label="新结论类型" required>
            <el-radio-group v-model="form.result_type">
              <el-radio-button v-for="(name, key) in RESULT_NAMES" :key="key" :value="key">
                {{ name }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.result_type === 'EXTRA'" label="加费比例（%）" required>
            <el-input v-model="form.extra_rate" class="w-40" />
          </el-form-item>
          <el-form-item v-if="form.result_type === 'EXCLUSION'" label="除外责任" required>
            <el-input v-model="form.exclusion_desc" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item v-if="form.result_type === 'POSTPONE'" label="延期月数" required>
            <el-input-number v-model="form.postpone_months" :min="1" :max="120" />
          </el-form-item>
          <el-form-item label="结论理由" required>
            <el-input v-model="form.new_reason" type="textarea" :rows="3" />
          </el-form-item>
        </template>
        <el-form-item label="复议意见" prop="comment">
          <el-input v-model="form.comment" type="textarea" :rows="3" placeholder="请说明复议处理依据" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onHandle">提交处理结果</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
