<script setup lang="ts">
// 复核中心（核保主管）：待复核列表，支持通过/退回
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { approveReview, fetchReviews, returnReview, type ReviewItem } from '@/api/manual'
import { RESULT_NAMES, RESULT_TYPES } from '@/utils/dict'

const router = useRouter()
const rows = ref<ReviewItem[]>([])
const loading = ref(true)

// 退回对话框
const returnVisible = ref(false)
const returnFormRef = ref<FormInstance>()
const returning = ref<ReviewItem | null>(null)
const returnForm = reactive({ comment: '' })
const returnRules: FormRules = {
  comment: [{ required: true, message: '请填写复核意见（退回理由）', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    rows.value = await fetchReviews('PENDING')
  } finally {
    loading.value = false
  }
}
onMounted(load)

/** 复核通过 */
async function onApprove(row: ReviewItem) {
  await approveReview(row.result_id)
  ElMessage.success('复核通过，结论已生效')
  await load()
}

/** 打开退回对话框 */
function openReturn(row: ReviewItem) {
  returning.value = row
  returnForm.comment = ''
  returnVisible.value = true
}

/** 确认退回 */
async function onReturn() {
  await returnFormRef.value?.validate()
  await returnReview(returning.value!.result_id, returnForm.comment)
  ElMessage.success('已退回核保员重新处理')
  returnVisible.value = false
  await load()
}
</script>

<template>
  <el-card>
    <template #header>复核中心（待复核结论）</template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="app_no" label="申请单号" width="170" />
      <el-table-column prop="product_name" label="险种" />
      <el-table-column prop="customer_name" label="客户" width="100" />
      <el-table-column label="核保结论" width="120">
        <template #default="{ row }">
          <el-tag :type="RESULT_TYPES[row.result_type] ?? 'info'">
            {{ RESULT_NAMES[row.result_type] ?? row.result_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="理由说明" min-width="220" show-overflow-tooltip />
      <el-table-column prop="underwriter_name" label="核保员" width="100" />
      <el-table-column prop="decided_at" label="出具时间" width="170" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/underwriting/tasks/${row.app_id}`)">
            查看案件
          </el-button>
          <el-button link type="success" @click="onApprove(row)">通过</el-button>
          <el-button link type="warning" @click="openReturn(row)">退回</el-button>
        </template>
      </el-table-column>
      <template #empty><el-empty description="暂无待复核结论" /></template>
    </el-table>

    <el-dialog v-model="returnVisible" title="退回核保结论" width="480px">
      <el-form ref="returnFormRef" :model="returnForm" :rules="returnRules" label-width="90px">
        <el-form-item label="复核意见" prop="comment">
          <el-input v-model="returnForm.comment" type="textarea" :rows="3"
            placeholder="请说明退回原因，案件将退回核保员重新处理" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="returnVisible = false">取消</el-button>
        <el-button type="warning" @click="onReturn">确认退回</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
