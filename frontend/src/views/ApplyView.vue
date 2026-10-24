<script setup lang="ts">
// 客户投保页：选择险种 -> 填写基本信息 -> 作答健康告知 -> 填写病史 -> 提交
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import {
  createApplication,
  fetchProducts,
  type AnswerItem,
  type Product,
} from '@/api/application'

const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(false)
const formRef = ref<FormInstance>()

// 表单数据：基本信息 + 问卷答案 + 病史
const form = reactive({
  product_id: null as number | null,
  applicant_name: '',
  gender: 'M' as 'M' | 'F',
  birth_date: '',
  id_card_no: '',
  phone: '',
  occupation: '',
  coverage_amount: '',
  coverage_period: '1年',
  pay_method: '年缴',
  answers: {} as Record<number, { answer: string; detail: string }>,
  medical_histories: [] as { disease_name: string; diagnosed_at: string; treatment: string }[],
  family_histories: [] as { relation: string; disease_name: string; diagnosed_at: string; treatment: string }[],
})

// 当前选中险种的启用题目（按 sort 排序）
const currentProduct = computed(() => products.value.find((x) => x.id === form.product_id))
const currentQuestions = computed(() => {
  const p = currentProduct.value
  return p ? [...p.questions].sort((a, b) => a.sort - b.sort) : []
})
const currentProductDescription = computed(() => currentProduct.value?.description ?? '')

const rules: FormRules = {
  product_id: [{ required: true, message: '请选择险种', trigger: 'change' }],
  applicant_name: [{ required: true, message: '请输入投保人姓名', trigger: 'blur' }],
  birth_date: [{ required: true, message: '请选择出生日期', trigger: 'change' }],
  id_card_no: [{ required: true, message: '请输入证件号码', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入联系电话', trigger: 'blur' }],
  coverage_amount: [
    { required: true, message: '请输入保额', trigger: 'blur' },
    { pattern: /^\d+(\.\d{1,2})?$/, message: '保额格式不正确', trigger: 'blur' },
  ],
  coverage_period: [{ required: true, message: '请选择保障期限', trigger: 'change' }],
  pay_method: [{ required: true, message: '请选择缴费方式', trigger: 'change' }],
}

onMounted(async () => {
  products.value = await fetchProducts()
})

/** 切换险种时按题目重置答卷结构，避免模板访问空对象（渲染异常导致后续区块不显示） */
function onProductChange() {
  const answers: Record<number, { answer: string; detail: string }> = {}
  for (const q of currentQuestions.value) {
    answers[q.id] = { answer: '', detail: '' }
  }
  form.answers = answers
}

/** 校验问卷：必答校验 + 风险题答"是"必填详细说明，返回是否通过 */
function validateQuestions(): boolean {
  for (const q of currentQuestions.value) {
    const a = form.answers[q.id]
    if (!a || !a.answer) {
      ElMessage.warning(`请作答健康告知第 ${q.sort} 题`)
      return false
    }
    if (q.answer_type === 'yes_no' && a.answer === 'yes' && !a.detail.trim()) {
      ElMessage.warning(`健康告知第 ${q.sort} 题回答为"是"，请填写详细说明`)
      return false
    }
  }
  return true
}

/** 提交投保申请 */
async function onSubmit() {
  await formRef.value?.validate()
  if (!validateQuestions()) return

  loading.value = true
  try {
    const answers: AnswerItem[] = currentQuestions.value.map((q) => ({
      question_id: q.id,
      answer: form.answers[q.id].answer,
      detail: form.answers[q.id].detail?.trim() || null,
    }))
    const result = await createApplication({
      product_id: form.product_id!,
      applicant_name: form.applicant_name,
      gender: form.gender,
      birth_date: form.birth_date,
      id_card_no: form.id_card_no,
      phone: form.phone,
      occupation: form.occupation || null,
      coverage_amount: form.coverage_amount,
      coverage_period: form.coverage_period,
      pay_method: form.pay_method,
      answers,
      medical_histories: form.medical_histories.map((h) => ({ ...h, treatment: h.treatment || null })),
      family_histories: form.family_histories.map((h) => ({ ...h, treatment: h.treatment || null })),
    })
    ElMessage.success(`投保申请已提交，申请单号：${result.app_no}`)
    router.push('/my-applications')
  } finally {
    loading.value = false
  }
}

// 病史动态行操作
function addMedical() {
  form.medical_histories.push({ disease_name: '', diagnosed_at: '', treatment: '' })
}
function removeMedical(i: number) {
  form.medical_histories.splice(i, 1)
}
function addFamily() {
  form.family_histories.push({ relation: 'FATHER', disease_name: '', diagnosed_at: '', treatment: '' })
}
function removeFamily(i: number) {
  form.family_histories.splice(i, 1)
}
</script>

<template>
  <el-card>
    <template #header>投保申请</template>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-divider content-position="left">投保计划</el-divider>
      <el-form-item label="选择险种" prop="product_id">
        <el-select v-model="form.product_id" placeholder="请选择险种" class="w-72" @change="onProductChange">
          <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <span v-if="currentProductDescription" class="ml-3 text-sm text-slate-500">
          {{ currentProductDescription }}
        </span>
      </el-form-item>

      <template v-if="form.product_id">
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="投保人姓名" prop="applicant_name">
          <el-input v-model="form.applicant_name" class="w-72" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="form.gender">
            <el-radio value="M">男</el-radio>
            <el-radio value="F">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="出生日期" prop="birth_date">
          <el-date-picker v-model="form.birth_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="证件号码" prop="id_card_no">
          <el-input v-model="form.id_card_no" class="w-72" placeholder="请输入证件号码" />
        </el-form-item>
        <el-form-item label="联系电话" prop="phone">
          <el-input v-model="form.phone" class="w-72" placeholder="请输入联系电话" />
        </el-form-item>
        <el-form-item label="职业">
          <el-input v-model="form.occupation" class="w-72" placeholder="请输入职业" />
        </el-form-item>
        <el-form-item label="保额（元）" prop="coverage_amount">
          <el-input v-model="form.coverage_amount" class="w-72" placeholder="如 1000000.00" />
        </el-form-item>
        <el-form-item label="保障期限" prop="coverage_period">
          <el-select v-model="form.coverage_period" class="w-72">
            <el-option label="1年" value="1年" />
            <el-option label="5年" value="5年" />
            <el-option label="10年" value="10年" />
            <el-option label="至70周岁" value="至70周岁" />
            <el-option label="终身" value="终身" />
          </el-select>
        </el-form-item>
        <el-form-item label="缴费方式" prop="pay_method">
          <el-select v-model="form.pay_method" class="w-72">
            <el-option label="年缴" value="年缴" />
            <el-option label="半年缴" value="半年缴" />
            <el-option label="季缴" value="季缴" />
            <el-option label="月缴" value="月缴" />
            <el-option label="趸交" value="趸交" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">健康告知</el-divider>
        <el-form-item v-for="q in currentQuestions" :key="q.id" :label="`第 ${q.sort} 题`">
          <div class="w-full">
            <div class="mb-2 text-sm text-slate-700">{{ q.content }}</div>
            <template v-if="q.answer_type === 'yes_no'">
              <el-radio-group v-model="form.answers[q.id].answer">
                <el-radio value="no">否</el-radio>
                <el-radio value="yes">是</el-radio>
              </el-radio-group>
              <el-input
                v-if="form.answers[q.id]?.answer === 'yes'"
                v-model="form.answers[q.id].detail"
                class="mt-2 w-full max-w-xl"
                type="textarea"
                :rows="2"
                placeholder="请说明何时、何地、诊断及治疗情况"
              />
            </template>
            <el-input v-else v-model="form.answers[q.id].answer" placeholder="请填写" class="max-w-xl" />
          </div>
        </el-form-item>

        <el-divider content-position="left">既往病史</el-divider>
        <div v-for="(h, i) in form.medical_histories" :key="i" class="flex gap-2 mb-2 items-center">
          <el-input v-model="h.disease_name" placeholder="疾病名称" class="w-48" />
          <el-date-picker v-model="h.diagnosed_at" type="date" value-format="YYYY-MM-DD" placeholder="诊断时间" />
          <el-input v-model="h.treatment" placeholder="治疗情况" class="w-64" />
          <el-button link type="danger" @click="removeMedical(i)">删除</el-button>
        </div>
        <el-button size="small" @click="addMedical">+ 添加既往病史</el-button>

        <el-divider content-position="left">家族病史</el-divider>
        <div v-for="(h, i) in form.family_histories" :key="i" class="flex gap-2 mb-2 items-center">
          <el-select v-model="h.relation" class="w-28">
            <el-option label="父亲" value="FATHER" />
            <el-option label="母亲" value="MOTHER" />
            <el-option label="兄弟姐妹" value="SIBLING" />
          </el-select>
          <el-input v-model="h.disease_name" placeholder="疾病名称" class="w-48" />
          <el-date-picker v-model="h.diagnosed_at" type="date" value-format="YYYY-MM-DD" placeholder="确诊时间" />
          <el-input v-model="h.treatment" placeholder="治疗情况" class="w-64" />
          <el-button link type="danger" @click="removeFamily(i)">删除</el-button>
        </div>
        <el-button size="small" @click="addFamily">+ 添加家族病史</el-button>

        <el-form-item class="mt-6">
          <el-button type="primary" :loading="loading" @click="onSubmit">提交投保申请</el-button>
        </el-form-item>
      </template>
    </el-form>
  </el-card>
</template>
