<script setup lang="ts">
// 核保员待办列表：按状态筛选案件
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { fetchTasks, type TaskItem } from '@/api/manual'
import { APP_STATUS_NAMES, APP_STATUS_TYPES } from '@/utils/dict'

const router = useRouter()
const rows = ref<TaskItem[]>([])
const loading = ref(true)
const activeTab = ref('MANUAL_REQUIRED')

async function load(status?: string) {
  loading.value = true
  try {
    rows.value = await fetchTasks(status)
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}
onMounted(() => load('MANUAL_REQUIRED'))

function onTabChange(name: string | number) {
  load(name === 'ALL' ? undefined : String(name))
}
</script>

<template>
  <el-card>
    <template #header>核保待办</template>
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="待人工核保" name="MANUAL_REQUIRED" />
      <el-tab-pane label="复核中" name="REVIEWING" />
      <el-tab-pane label="已出结论" name="DECIDED" />
      <el-tab-pane label="全部案件" name="ALL" />
    </el-tabs>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="app_no" label="申请单号" width="170" />
      <el-table-column prop="product_name" label="险种" />
      <el-table-column prop="customer_name" label="客户" width="100" />
      <el-table-column prop="applicant_name" label="投保人" width="100" />
      <el-table-column label="保额（元）" width="130" align="right">
        <template #default="{ row }">{{ Number(row.coverage_amount).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="APP_STATUS_TYPES[row.status] ?? 'info'">
            {{ APP_STATUS_NAMES[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="申请时间" width="170" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/underwriting/tasks/${row.id}`)">
            处理案件
          </el-button>
        </template>
      </el-table-column>
      <template #empty><el-empty description="暂无案件" /></template>
    </el-table>
  </el-card>
</template>
