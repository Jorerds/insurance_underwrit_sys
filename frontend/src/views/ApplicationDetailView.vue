<script setup lang="ts">
// 申请详情（客户）：投保资料 + 问卷答卷 + 病史 + 核保结论 + 复议
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { fetchApplicationDetail, type ApplicationDetail } from '@/api/application'
import { startReconsideration } from '@/api/reconsider'
import { APP_STATUS_NAMES, APP_STATUS_TYPES, RESULT_NAMES, RESULT_TYPES, answerText } from '@/utils/dict'

const route = useRoute()
const detail = ref<ApplicationDetail | null>(null)
const loading = ref(true)

// 复议对话框
const recVisible = ref(false)
const recSaving = ref(false)
const recForm = reactive({ reason: '' })

const RELATION_NAMES: Record<string, string> = { FATHER: '父亲', MOTHER: '母亲', SIBLING: '兄弟姐妹' }

onMounted(async () => {
  try {
    detail.value = await fetchApplicationDetail(Number(route.params.id))
  } finally {
    loading.value = false
  }
})

/** 提交复议申请 */
async function onSubmitReconsider() {
  if (!recForm.reason.trim()) {
    ElMessage.warning('请填写复议理由')
    return
  }
  recSaving.value = true
  try {
    await startReconsideration(Number(route.params.id), recForm.reason)
    ElMessage.success('复议申请已提交，请等待核保主管处理')
    recVisible.value = false
    detail.value = await fetchApplicationDetail(Number(route.params.id))
  } finally {
    recSaving.value = false
  }
}
</script>

<template>
  <div v-loading="loading">
    <el-card v-if="detail">
      <template #header>
        <div class="flex justify-between items-center">
          <span>申请详情（{{ detail.app_no }}）</span>
          <el-tag :type="APP_STATUS_TYPES[detail.status] ?? 'info'">
            {{ APP_STATUS_NAMES[detail.status] ?? detail.status }}
          </el-tag>
        </div>
      </template>

      <!-- 核保结论：已出具时展示 -->
      <template v-if="detail.result">
        <el-divider content-position="left">核保结论</el-divider>
        <el-descriptions :column="2" border class="mb-6">
          <el-descriptions-item label="结论">
            <el-tag :type="RESULT_TYPES[detail.result.result_type] ?? 'info'">
              {{ RESULT_NAMES[detail.result.result_type] ?? detail.result.result_type }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="出具时间">{{ detail.result.decided_at }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.result.extra_rate" label="加费比例">
            {{ detail.result.extra_rate }}%
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.result.exclusion_desc" label="除外责任">
            {{ detail.result.exclusion_desc }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.result.postpone_months" label="延期时长">
            {{ detail.result.postpone_months }} 个月
          </el-descriptions-item>
          <el-descriptions-item label="理由说明" :span="2">
            {{ detail.result.reason }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 复议区块：已出结论后可申请复议 -->
        <template v-if="detail.status === 'DECIDED'">
          <el-button type="warning" plain @click="recVisible = true">申请复议</el-button>
        </template>
      </template>

      <!-- 复议进度 -->
      <template v-if="detail.reconsideration">
        <el-divider content-position="left">复议记录</el-divider>
        <el-descriptions :column="2" border class="mb-6">
          <el-descriptions-item label="复议理由" :span="2">
            {{ detail.reconsideration.reason }}
          </el-descriptions-item>
          <el-descriptions-item label="处理状态">
            <el-tag :type="detail.reconsideration.status === 'DONE' ? 'success' : 'warning'">
              {{ detail.reconsideration.status === 'DONE' ? '复议完成' : '复议处理中' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="处理时间">
            {{ detail.reconsideration.handled_at ?? '待处理' }}
          </el-descriptions-item>
          <template v-if="detail.reconsideration.status === 'DONE'">
            <el-descriptions-item label="复议意见" :span="2">
              {{ detail.reconsideration.comment }}
            </el-descriptions-item>
            <el-descriptions-item label="最终结论">
              <el-tag :type="RESULT_TYPES[detail.reconsideration.final_result_type ?? ''] ?? 'info'">
                {{ RESULT_NAMES[detail.reconsideration.final_result_type ?? ''] ?? '-' }}
              </el-tag>
            </el-descriptions-item>
          </template>
        </el-descriptions>
      </template>

      <el-descriptions title="基本信息" :column="2" border class="mb-6">
        <el-descriptions-item label="险种">{{ detail.product_name }}</el-descriptions-item>
        <el-descriptions-item label="投保人">{{ detail.applicant_name }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ detail.gender === 'M' ? '男' : '女' }}</el-descriptions-item>
        <el-descriptions-item label="出生日期">{{ detail.birth_date }}</el-descriptions-item>
        <el-descriptions-item label="证件号码">{{ detail.id_card_no }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detail.phone }}</el-descriptions-item>
        <el-descriptions-item label="职业">{{ detail.occupation || '-' }}</el-descriptions-item>
        <el-descriptions-item label="保额（元）">{{ Number(detail.coverage_amount).toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="保障期限">{{ detail.coverage_period }}</el-descriptions-item>
        <el-descriptions-item label="缴费方式">{{ detail.pay_method }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">健康告知答卷</el-divider>
      <el-table :data="detail.answers" class="mb-6">
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
      <el-table :data="detail.medical_histories" class="mb-6">
        <el-table-column prop="disease_name" label="疾病名称" />
        <el-table-column prop="diagnosed_at" label="诊断时间" width="130" />
        <el-table-column prop="treatment" label="治疗情况">
          <template #default="{ row }">{{ row.treatment || '-' }}</template>
        </el-table-column>
        <template #empty><el-empty description="无既往病史" :image-size="60" /></template>
      </el-table>

      <el-divider content-position="left">家族病史</el-divider>
      <el-table :data="detail.family_histories">
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
    </el-card>

    <!-- 申请复议对话框 -->
    <el-dialog v-model="recVisible" title="申请复议" width="520px">
      <el-alert type="info" :closable="false" class="mb-4"
        title="请在结论出具后 30 天内申请，每个案件仅可申请一次复议，复议结论为最终结论。" />
      <el-form label-width="80px">
        <el-form-item label="复议理由" required>
          <el-input v-model="recForm.reason" type="textarea" :rows="4"
            placeholder="请说明对核保结论的异议及补充情况" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recVisible = false">取消</el-button>
        <el-button type="primary" :loading="recSaving" @click="onSubmitReconsider">提交复议申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>
