<script setup lang="ts">
// 险种管理（admin）：列表、新增、编辑、启停
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import {
  createAdminProduct,
  fetchAdminProducts,
  updateAdminProduct,
  type AdminProduct,
} from '@/api/application'

const rows = ref<AdminProduct[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const editing = ref<AdminProduct | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({ code: '', name: '', description: '', status: 1 })
const rules: FormRules = {
  code: [{ required: true, message: '请输入险种代码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入险种名称', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    rows.value = await fetchAdminProducts()
  } finally {
    loading.value = false
  }
}
onMounted(load)

/** 打开新增/编辑对话框 */
function openDialog(row: AdminProduct | null) {
  editing.value = row
  form.code = row?.code ?? ''
  form.name = row?.name ?? ''
  form.description = row?.description ?? ''
  form.status = row?.status ?? 1
  dialogVisible.value = true
}

/** 保存险种 */
async function onSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editing.value) {
      await updateAdminProduct(editing.value.id, { ...form })
    } else {
      await createAdminProduct({ ...form })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

/** 启停切换 */
async function onToggleStatus(row: AdminProduct, status: number) {
  await updateAdminProduct(row.id, {
    code: row.code, name: row.name, description: row.description, status,
  })
  ElMessage.success(status === 1 ? '已启用' : '已停用')
  await load()
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="flex justify-between items-center">
        <span>险种管理</span>
        <el-button type="primary" @click="openDialog(null)">新增险种</el-button>
      </div>
    </template>
    <el-table v-loading="loading" :data="rows">
      <el-table-column prop="code" label="险种代码" width="140" />
      <el-table-column prop="name" label="险种名称" />
      <el-table-column prop="description" label="简介" min-width="200">
        <template #default="{ row }">{{ row.description || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">
            {{ row.status === 1 ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="primary" @click="$router.push(`/admin/products/${row.id}/questions`)">
            问卷配置
          </el-button>
          <el-button v-if="row.status === 1" link type="warning" @click="onToggleStatus(row, 0)">
            停用
          </el-button>
          <el-button v-else link type="success" @click="onToggleStatus(row, 1)">启用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑险种' : '新增险种'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="险种代码" prop="code">
          <el-input v-model="form.code" :disabled="Boolean(editing)" placeholder="如 MED001" />
        </el-form-item>
        <el-form-item label="险种名称" prop="name">
          <el-input v-model="form.name" placeholder="如 百万医疗险" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.description" type="textarea" :rows="3" />
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
