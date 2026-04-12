<template>
  <el-card class="task-input-card">
    <template #header>
      <div class="card-header">
        <span>创建新任务</span>
      </div>
    </template>
    
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      size="default"
    >
      <!-- ASIN 输入 -->
      <el-form-item label="ASIN" prop="asin">
        <el-input
          v-model="form.asin"
          placeholder="请输入 10 位 ASIN"
          maxlength="10"
          show-word-limit
          clearable
        />
      </el-form-item>
      
      <!-- 站点选择 -->
      <el-form-item label="亚马逊站点" prop="site">
        <el-select v-model="form.site" placeholder="请选择站点" style="width: 100%">
          <el-option label="美国 (amazon.com)" value="amazon.com" />
          <el-option label="英国 (amazon.co.uk)" value="amazon.co.uk" />
          <el-option label="德国 (amazon.de)" value="amazon.de" />
          <el-option label="法国 (amazon.fr)" value="amazon.fr" />
          <el-option label="日本 (amazon.co.jp)" value="amazon.co.jp" />
          <el-option label="加拿大 (amazon.ca)" value="amazon.ca" />
          <el-option label="澳大利亚 (amazon.com.au)" value="amazon.com.au" />
        </el-select>
      </el-form-item>
      
      <!-- 最大翻页数 -->
      <el-form-item label="最大翻页数" prop="maxPages">
        <el-input-number
          v-model="form.maxPages"
          :min="1"
          :max="50"
          :step="1"
          controls-position="right"
          style="width: 100%"
        />
      </el-form-item>
      
      <!-- 关键词输入 -->
      <el-form-item label="关键词" prop="keywords">
        <el-input
          v-model="keywordInput"
          type="textarea"
          :rows="6"
          placeholder="每行一个关键词，最多 100 个"
          @blur="parseKeywords"
        />
        <div class="keyword-count">
          已输入 {{ form.keywords.length }} 个关键词（最多 100 个）
        </div>
      </el-form-item>
      
      <!-- 提交按钮 -->
      <el-form-item>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSubmit"
          style="width: 100%"
        >
          {{ loading ? '提交中...' : '提交任务' }}
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import { createTask } from '../api/tasks';
import type { TaskCreateRequest } from '../types';

// 定义 emits
const emit = defineEmits<{
  (e: 'submitted', taskId: string): void;
}>();

// 表单引用
const formRef = ref<FormInstance>();

// 表单数据
const form = reactive<TaskCreateRequest>({
  asin: '',
  site: 'amazon.com',
  maxPages: 5,
  keywords: [],
});

// 关键词文本输入
const keywordInput = ref('');

// 加载状态
const loading = ref(false);

// 表单验证规则
const rules: FormRules = {
  asin: [
    { required: true, message: '请输入 ASIN', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9]{10}$/,
      message: 'ASIN 必须为 10 位字母数字',
      trigger: 'blur',
    },
  ],
  site: [
    { required: true, message: '请选择站点', trigger: 'change' },
  ],
  maxPages: [
    { required: true, message: '请输入翻页数', trigger: 'blur' },
  ],
  keywords: [
    {
      required: true,
      message: '请至少输入一个关键词',
      trigger: 'blur',
    },
    {
      validator: (rule, value, callback) => {
        if (value.length > 100) {
          callback(new Error('关键词不能超过 100 个'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
};

// 解析关键词
const parseKeywords = () => {
  const keywords = keywordInput.value
    .split('\n')
    .map((k) => k.trim())
    .filter((k) => k.length > 0 && k.length <= 200);
  
  form.keywords = keywords.slice(0, 100);
};

// 监听关键词变化，更新文本框
watch(
  () => form.keywords,
  (newKeywords) => {
    if (keywordInput.value) {
      const currentKeywords = keywordInput.value
        .split('\n')
        .map((k) => k.trim())
        .filter((k) => k.length > 0);
      
      if (currentKeywords.length !== newKeywords.length) {
        keywordInput.value = newKeywords.join('\n');
      }
    }
  }
);

// 提交任务
const handleSubmit = async () => {
  if (!formRef.value) return;
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    
    loading.value = true;
    
    try {
      const response = await createTask(form);
      ElMessage.success('任务提交成功！');
      emit('submitted', response.taskId);
      
      // 重置表单
      form.asin = '';
      form.keywords = [];
      keywordInput.value = '';
      formRef.value.resetFields();
    } catch (error: any) {
      const message = error.response?.data?.message || '提交失败，请稍后重试';
      ElMessage.error(message);
    } finally {
      loading.value = false;
    }
  });
};
</script>

<style scoped>
.task-input-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.keyword-count {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
