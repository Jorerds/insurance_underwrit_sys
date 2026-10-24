<script setup lang="ts">
// 体检项目管理（admin）
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import {
  createAdminExamItem,
  fetchAdminExamItems,
  updateAdminExamItem,
  type ExamItem,
} from '@/api/exam'

const rows = ref<ExamItem[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const editing = ref<ExamItem | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({ name: '', unit: '', ref_range: '', sort: 0, status: 1 })
const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    rows.value = await fetchAdminExamItems()
  } finally {
    loading.value = false
  }
}
onMounted(load)

function openDialog(row: ExamItem | null) {
  editing.value = row
  form.name = row?.name ?? ''
  form.unit = row?.unit ?? ''
  form.ref_range = row?.ref_range ?? ''
  form.sort = row?.sort ?? 0
  form.status = row?.status ?? 1
  dialogVisible.value = true
}

async function onSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editing.value) {
      await updateAdminExamItem(editing.value.id, { ...form })
    } else {
      await createAdminExamItem({ ...form })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onToggle(row: ExamItem, status: number) {
  await updateAdminExamItem(row.id, {
    name: row.name, unit: row.unit, ref_range: row.ref_range, sort: row.sort, status,
  })
  ElMessage.success(status === 1 ? '已启用' : '已停用')
  await load()
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="flex justify-between items-center">
        <span>体检项目管理</span>
        <el-button type="primary" @click="openDialog(null)">新增项目</el-button>
      </div>
    </template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column prop="name" label="项目名称" min-width="160" />
      <el-table-column prop="unit" label="单位" width="100">
        <template #default="{ row }">{{ row.unit || '-' }}</template>
      </el-table-column>
      <el-table-column prop="ref_range" label="参考范围" min-width="140">
        <template #default="{ row }">{{ row.ref_range || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="row.status === 1" link type="warning" @click="onToggle(row, 0)">停用</el-button>
          <el-button v-else link type="success" @click="onToggle(row, 1)">启用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑项目' : '新增项目'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="如：血常规" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" placeholder="如：mmol/L" />
        </el-form-item>
        <el-form-item label="参考范围">
          <el-input v-model="form.ref_range" placeholder="如：3.9-6.1" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" />
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
