<script setup lang="ts">
// 统计看板（核保员/主管）：时间筛选 + 卡片 + 图表 + 明细 + 导出
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { exportUrl, fetchDashboard, type Dashboard } from '@/api/stats'
import http from '@/api'
import { RESULT_NAMES, RESULT_TYPES } from '@/utils/dict'

const dashboard = ref<Dashboard | null>(null)
const loading = ref(true)

// 时间范围：默认近 30 天
const today = new Date()
const defaultFrom = new Date(today.getTime() - 29 * 86400000)
const fmt = (d: Date) => d.toISOString().slice(0, 10)
const dateRange = ref<[string, string]>([fmt(defaultFrom), fmt(today)])

// 图表容器引用
const productChartRef = ref<HTMLDivElement>()
const resultChartRef = ref<HTMLDivElement>()
const ageChartRef = ref<HTMLDivElement>()
let productChart: echarts.ECharts | null = null
let resultChart: echarts.ECharts | null = null
let ageChart: echarts.ECharts | null = null

const resultSourceNames: Record<string, string> = {
  AUTO: '智能核保', MANUAL: '人工核保', RECONSIDER: '复议',
}

async function load() {
  loading.value = true
  try {
    dashboard.value = await fetchDashboard(dateRange.value[0], dateRange.value[1])
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}
onMounted(load)

/** 渲染三个图表 */
function renderCharts() {
  const d = dashboard.value
  if (!d) return

  productChart?.dispose()
  productChart = echarts.init(productChartRef.value!)
  productChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['核保量', '通过数'] },
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: d.by_product.map((p) => p.product_name) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '核保量', type: 'bar', data: d.by_product.map((p) => p.total), itemStyle: { color: '#409eff' } },
      { name: '通过数', type: 'bar', data: d.by_product.map((p) => p.passed), itemStyle: { color: '#67c23a' } },
    ],
  })

  resultChart?.dispose()
  resultChart = echarts.init(resultChartRef.value!)
  resultChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}：{c}（{d}%）' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '65%'],
      data: d.by_result.filter((r) => r.count > 0).map((r) => ({
        name: RESULT_NAMES[r.result_type] ?? r.result_type, value: r.count,
      })),
    }],
  })

  ageChart?.dispose()
  ageChart = echarts.init(ageChartRef.value!)
  ageChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: d.by_age.map((a) => a.age_range) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '核保量', type: 'bar', data: d.by_age.map((a) => a.total), itemStyle: { color: '#909399' } },
      {
        name: '通过率%', type: 'line', yAxisIndex: 0, smooth: true,
        data: d.by_age.map((a) => a.pass_rate), itemStyle: { color: '#e6a23c' },
      },
    ],
  })
}

const onResize = () => {
  productChart?.resize()
  resultChart?.resize()
  ageChart?.resize()
}
window.addEventListener('resize', onResize)

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  productChart?.dispose()
  resultChart?.dispose()
  ageChart?.dispose()
})

watch(dateRange, load)

/** 通过 axios 拉取导出文件并触发浏览器保存 */
async function onExport(format: 'xlsx' | 'csv') {
  const resp = await http.get(exportUrl(format, dateRange.value[0], dateRange.value[1]), {
    responseType: 'blob',
  })
  const disposition: string = resp.headers['content-disposition'] ?? ''
  const match = disposition.match(/filename\*=UTF-8''([^;]+)/)
  const filename = match ? decodeURIComponent(match[1]) : `核保统计.${format}`
  const url = URL.createObjectURL(resp.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

const cards = computed(() => {
  const s = dashboard.value?.summary
  if (!s) return []
  return [
    { title: '核保量', value: s.total, unit: '件' },
    { title: '通过率', value: s.pass_rate, unit: '%' },
    { title: '标体承保', value: s.by_result['STANDARD'] ?? 0, unit: '件' },
    { title: '拒保', value: s.by_result['DECLINE'] ?? 0, unit: '件' },
  ]
})
</script>

<template>
  <div v-loading="loading">
    <!-- 筛选与导出 -->
    <el-card class="mb-4">
      <div class="flex items-center justify-between flex-wrap gap-4">
        <div class="flex items-center gap-4">
          <span class="text-slate-600 text-sm">统计时间（按结论出具时间）</span>
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
            range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
        </div>
        <div class="flex gap-2">
          <el-button @click="onExport('xlsx')">导出 Excel</el-button>
          <el-button @click="onExport('csv')">导出 CSV</el-button>
        </div>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
      <el-card v-for="c in cards" :key="c.title" shadow="never" body-class="!p-4">
        <div class="text-sm text-slate-500">{{ c.title }}</div>
        <div class="text-2xl font-bold text-slate-800 mt-1">
          {{ c.value }}<span class="text-sm font-normal text-slate-400 ml-1">{{ c.unit }}</span>
        </div>
      </el-card>
    </div>

    <!-- 图表 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
      <el-card shadow="never">
        <template #header>按险种：核保量与通过数</template>
        <div ref="productChartRef" class="h-64" />
      </el-card>
      <el-card shadow="never">
        <template #header>按结论分布</template>
        <div ref="resultChartRef" class="h-64" />
      </el-card>
      <el-card shadow="never">
        <template #header>按年龄段：核保量与通过率</template>
        <div ref="ageChartRef" class="h-64" />
      </el-card>
    </div>

    <!-- 明细表 -->
    <el-card shadow="never">
      <template #header>核保明细</template>
      <el-table :data="dashboard?.detail ?? []" max-height="420">
        <el-table-column prop="app_no" label="申请单号" width="170" />
        <el-table-column prop="product_name" label="险种" />
        <el-table-column prop="applicant_name" label="投保人" width="100" />
        <el-table-column prop="age" label="年龄" width="70" align="center" />
        <el-table-column label="核保结论" width="120">
          <template #default="{ row }">
            <el-tag :type="RESULT_TYPES[row.result_type] ?? 'info'">
              {{ RESULT_NAMES[row.result_type] ?? row.result_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结论来源" width="110">
          <template #default="{ row }">{{ resultSourceNames[row.source] ?? row.source }}</template>
        </el-table-column>
        <el-table-column prop="decided_at" label="出具日期" width="120" />
        <template #empty><el-empty description="该时间范围内暂无核保数据" /></template>
      </el-table>
    </el-card>
  </div>
</template>
