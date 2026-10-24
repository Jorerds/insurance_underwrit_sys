<script setup lang="ts">
// 体检结果录入（体检机构）：本机构单据列表，逐项录入结果
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  enterExamResult,
  fetchExamOrders,
  type ExamOrder,
} from '@/api/exam'
import { EXAM_STATUS_NAMES } from '@/utils/dict'

const rows = ref<ExamOrder[]>([])
const loading = ref(true)

// 录入对话框
const entryVisible = ref(false)
const entrySaving = ref(false)
const current = ref<ExamOrder | null>(null)
// 逐项录入值：{ item_id: { result_value, is_abnormal, remark } }
const entryForm = reactive({ overall_result: '', items: {} as Record<number, { result_value: string; is_abnormal: boolean; remark: string }> })

async function load() {
  loading.value = true
  try {
    rows.value = await fetchExamOrders()
  } finally {
    loading.value = false
  }
}
onMounted(load)

/** 打开录入对话框 */
function openEntry(row: ExamOrder) {
  current.value = row
  entryForm.overall_result = ''
  entryForm.items = {}
  for (const i of row.items) {
    entryForm.items[i.item_id] = { result_value: '', is_abnormal: false, remark: '' }
  }
  entryVisible.value = true
}

/** 提交录入结果 */
async function onSubmitEntry() {
  if (!entryForm.overall_result.trim()) {
    ElMessage.warning('请填写体检总结论')
    return
  }
  const itemResults = Object.entries(entryForm.items).map(([itemId, v]) => ({
    item_id: Number(itemId),
    result_value: v.result_value,
    is_abnormal: v.is_abnormal ? 1 : 0,
    remark: v.remark || null,
  }))
  if (itemResults.some((r) => !r.result_value.trim())) {
    ElMessage.warning('存在未填写结果值的项目')
    return
  }
  entrySaving.value = true
  try {
    await enterExamResult(current.value!.id, {
      overall_result: entryForm.overall_result,
      item_results: itemResults,
    })
    ElMessage.success('结果已提交，案件将重新评估')
    entryVisible.value = false
    await load()
  } finally {
    entrySaving.value = false
  }
}
</script>

<template>
  <el-card>
    <template #header>体检结果录入（本机构）</template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="id" label="体检单号" width="90" />
      <el-table-column prop="app_no" label="申请单号" width="170" />
      <el-table-column prop="center_name" label="体检机构" />
      <el-table-column label="项目数" width="80" align="center">
        <template #default="{ row }">{{ row.items.length }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">{{ EXAM_STATUS_NAMES[row.status] ?? row.status }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="开单时间" width="170" />
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button v-if="row.status === 'PENDING'" link type="primary" @click="openEntry(row)">
            录入结果
          </el-button>
          <span v-else class="text-slate-400 text-sm">已录入</span>
        </template>
      </el-table-column>
      <template #empty><el-empty description="暂无体检单" /></template>
    </el-table>

    <el-dialog v-model="entryVisible" :title="`录入体检结果（单号 ${current?.id}）`" width="720px">
      <el-form label-width="90px">
        <div v-for="i in current?.items" :key="i.item_id" class="flex gap-2 mb-3 items-center">
          <span class="w-28 text-sm text-right text-slate-600">{{ i.item_name }}</span>
          <el-input v-model="entryForm.items[i.item_id].result_value" placeholder="结果值" class="w-56" />
          <el-checkbox v-model="entryForm.items[i.item_id].is_abnormal">异常</el-checkbox>
          <el-input v-model="entryForm.items[i.item_id].remark" placeholder="备注（可选）" class="flex-1" />
        </div>
        <el-form-item label="总结论" required>
          <el-input v-model="entryForm.overall_result" type="textarea" :rows="3"
            placeholder="如：血常规异常，建议复查；其余各项正常" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="entryVisible = false">取消</el-button>
        <el-button type="primary" :loading="entrySaving" @click="onSubmitEntry">提交结果</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
