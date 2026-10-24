<script setup lang="ts">
// 体检机构管理（admin）
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import {
  createAdminCenter,
  fetchAdminCenters,
  updateAdminCenter,
  type ExamCenter,
} from '@/api/exam'

const rows = ref<ExamCenter[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const editing = ref<ExamCenter | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({ name: '', contact_phone: '', address: '', status: 1 })
const rules: FormRules = {
  name: [{ required: true, message: '请输入机构名称', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    rows.value = await fetchAdminCenters()
  } finally {
    loading.value = false
  }
}
onMounted(load)

function openDialog(row: ExamCenter | null) {
  editing.value = row
  form.name = row?.name ?? ''
  form.contact_phone = row?.contact_phone ?? ''
  form.address = row?.address ?? ''
  form.status = row?.status ?? 1
  dialogVisible.value = true
}

async function onSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editing.value) {
      await updateAdminCenter(editing.value.id, { ...form })
    } else {
      await createAdminCenter({ ...form })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onToggle(row: ExamCenter, status: number) {
  await updateAdminCenter(row.id, {
    name: row.name, contact_phone: row.contact_phone, address: row.address, status,
  })
  ElMessage.success(status === 1 ? '已启用' : '已停用')
  await load()
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="flex justify-between items-center">
        <span>体检机构管理</span>
        <el-button type="primary" @click="openDialog(null)">新增机构</el-button>
      </div>
    </template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="name" label="机构名称" min-width="160" />
      <el-table-column prop="contact_phone" label="联系电话" width="140">
        <template #default="{ row }">{{ row.contact_phone || '-' }}</template>
      </el-table-column>
      <el-table-column prop="address" label="地址" min-width="200">
        <template #default="{ row }">{{ row.address || '-' }}</template>
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

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑机构' : '新增机构'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="机构名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" />
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
