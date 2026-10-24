<script setup lang="ts">
// 我的申请列表（客户）
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchMyApplications, type ApplicationListItem } from '@/api/application'
import { APP_STATUS_NAMES, APP_STATUS_TYPES } from '@/utils/dict'

const router = useRouter()
const rows = ref<ApplicationListItem[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    rows.value = await fetchMyApplications()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <el-card>
    <template #header>
      <div class="flex justify-between items-center">
        <span>我的投保申请</span>
        <el-button type="primary" @click="router.push('/apply')">发起投保</el-button>
      </div>
    </template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="app_no" label="申请单号" width="180" />
      <el-table-column prop="product_name" label="险种" />
      <el-table-column prop="applicant_name" label="投保人" width="100" />
      <el-table-column label="保额（元）" width="140" align="right">
        <template #default="{ row }">{{ Number(row.coverage_amount).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="APP_STATUS_TYPES[row.status] ?? 'info'">
            {{ APP_STATUS_NAMES[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="申请时间" width="170" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/my-applications/${row.id}`)">
            查看详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
