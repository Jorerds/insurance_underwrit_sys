<script setup lang="ts">
// 告知问卷题目配置（admin）：按险种维护题目，支持启停
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import {
  createAdminQuestion,
  fetchAdminQuestions,
  updateAdminQuestion,
  type AdminQuestion,
} from '@/api/application'

const route = useRoute()
const productId = Number(route.params.id)
const rows = ref<AdminQuestion[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const editing = ref<AdminQuestion | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  content: '', sort: 0, is_risk: 0, answer_type: 'yes_no', is_required: 1, status: 1,
})
const rules: FormRules = {
  content: [{ required: true, message: '请输入题干', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    rows.value = await fetchAdminQuestions(productId)
  } finally {
    loading.value = false
  }
}
onMounted(load)

/** 打开新增/编辑对话框 */
function openDialog(row: AdminQuestion | null) {
  editing.value = row
  form.content = row?.content ?? ''
  form.sort = row?.sort ?? 0
  form.is_risk = row?.is_risk ?? 0
  form.answer_type = row?.answer_type ?? 'yes_no'
  form.is_required = row?.is_required ?? 1
  form.status = row?.status ?? 1
  dialogVisible.value = true
}

/** 保存题目 */
async function onSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editing.value) {
      await updateAdminQuestion(editing.value.id, { ...form })
    } else {
      await createAdminQuestion(productId, { ...form })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

/** 启停切换（行内快捷操作） */
async function onToggle(row: AdminQuestion, status: number) {
  await updateAdminQuestion(row.id, { ...row, status })
  ElMessage.success(status === 1 ? '已启用' : '已停用')
  await load()
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="flex justify-between items-center">
        <span>告知问卷配置</span>
        <el-button type="primary" @click="openDialog(null)">新增题目</el-button>
      </div>
    </template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column prop="content" label="题干" min-width="280" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">{{ row.answer_type === 'yes_no' ? '是/否' : '文本' }}</template>
      </el-table-column>
      <el-table-column label="风险题" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_risk === 1 ? 'danger' : 'info'" size="small">
            {{ row.is_risk === 1 ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="必答" width="80">
        <template #default="{ row }">{{ row.is_required === 1 ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="row.status === 1" link type="warning" @click="onToggle(row, 0)">
            停用
          </el-button>
          <el-button v-else link type="success" @click="onToggle(row, 1)">启用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑题目' : '新增题目'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="题干" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="2" placeholder="如：是否曾被诊断患有高血压？" />
        </el-form-item>
        <el-form-item label="题目类型">
          <el-radio-group v-model="form.answer_type">
            <el-radio value="yes_no">是/否（选"是"须填详细说明）</el-radio>
            <el-radio value="text">自由文本</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" />
        </el-form-item>
        <el-form-item label="风险题">
          <el-switch v-model="form.is_risk" :active-value="1" :inactive-value="0"
            active-text="是" inactive-text="否" />
        </el-form-item>
        <el-form-item label="是否必答">
          <el-switch v-model="form.is_required" :active-value="1" :inactive-value="0"
            active-text="必答" inactive-text="选答" />
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
