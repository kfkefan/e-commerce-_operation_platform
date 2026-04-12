<template>
  <el-card class="result-table-card">
    <template #header>
      <div class="card-header">
        <span>排名结果</span>
        <el-button
          type="primary"
          size="small"
          @click="handleExport"
        >
          导出 CSV
        </el-button>
      </div>
    </template>
    
    <el-table
      :data="results"
      style="width: 100%"
      border
      stripe
      :default-sort="{ prop: 'keyword', order: 'ascending' }"
      v-loading="loading"
    >
      <!-- 关键词 -->
      <el-table-column
        prop="keyword"
        label="关键词"
        sortable
        min-width="200"
        show-overflow-tooltip
      />
      
      <!-- 自然排名 -->
      <el-table-column
        label="自然排名"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <span v-if="row.organicPage && row.organicPosition" class="rank-found">
            第{{ row.organicPage }}页 - 第{{ row.organicPosition }}位
          </span>
          <span v-else class="rank-not-found">未找到</span>
        </template>
      </el-table-column>
      
      <!-- 广告排名 -->
      <el-table-column
        label="广告排名"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <span v-if="row.adPage && row.adPosition" class="rank-found">
            第{{ row.adPage }}页 - 第{{ row.adPosition }}位
          </span>
          <span v-else class="rank-not-found">未找到</span>
        </template>
      </el-table-column>
      
      <!-- 状态 -->
      <el-table-column
        prop="status"
        label="状态"
        width="150"
        align="center"
      >
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <!-- 爬取时间 -->
      <el-table-column
        prop="timestamp"
        label="爬取时间"
        width="180"
        sortable
        align="center"
      >
        <template #default="{ row }">
          {{ formatDate(row.timestamp) }}
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 统计信息 -->
    <div class="statistics" v-if="results.length > 0">
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="总关键词数">
          {{ results.length }}
        </el-descriptions-item>
        <el-descriptions-item label="找到排名">
          <span class="stat-success">{{ stats.found }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="仅自然未找到">
          {{ stats.organicNotFound }}
        </el-descriptions-item>
        <el-descriptions-item label="仅广告未找到">
          {{ stats.adNotFound }}
        </el-descriptions-item>
        <el-descriptions-item label="都未找到">
          {{ stats.notFound }}
        </el-descriptions-item>
        <el-descriptions-item label="错误">
          <span class="stat-error">{{ stats.error }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="验证码">
          <span class="stat-warning">{{ stats.captcha }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="成功率">
          <el-progress
            :percentage="successRate"
            :stroke-width="12"
            :show-text="false"
            status="success"
          />
          <span class="rate-text">{{ successRate }}%</span>
        </el-descriptions-item>
      </el-descriptions>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { RankingResult } from '../types';
import { ElMessage } from 'element-plus';

// 定义 props
const props = defineProps<{
  results: RankingResult[];
  loading?: boolean;
}>();

// 加载状态
const loading = ref(props.loading || false);

// 统计信息
const stats = computed(() => {
  const result = {
    found: 0,
    organicNotFound: 0,
    adNotFound: 0,
    notFound: 0,
    error: 0,
    captcha: 0,
  };
  
  props.results.forEach((r) => {
    switch (r.status) {
      case 'found':
        result.found++;
        break;
      case 'organic_not_found':
        result.organicNotFound++;
        break;
      case 'ad_not_found':
        result.adNotFound++;
        break;
      case 'not_found':
        result.notFound++;
        break;
      case 'error':
        result.error++;
        break;
      case 'captcha':
        result.captcha++;
        break;
    }
  });
  
  return result;
});

// 成功率
const successRate = computed(() => {
  if (props.results.length === 0) return 0;
  return Math.round((stats.value.found / props.results.length) * 100);
});

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    found: 'success',
    organic_not_found: 'warning',
    ad_not_found: 'warning',
    not_found: 'info',
    error: 'danger',
    captcha: 'warning',
  };
  return types[status] || 'info';
};

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    found: '已找到',
    organic_not_found: '仅自然未找到',
    ad_not_found: '仅广告未找到',
    not_found: '未找到',
    error: '错误',
    captcha: '验证码',
  };
  return texts[status] || status;
};

// 格式化日期
const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

// 导出 CSV
const handleExport = () => {
  if (props.results.length === 0) {
    ElMessage.warning('没有数据可导出');
    return;
  }
  
  // 构建 CSV 内容
  const headers = ['关键词', '自然排名页', '自然排名位置', '广告排名页', '广告排名位置', '状态', '爬取时间'];
  const rows = props.results.map((r) => [
    r.keyword,
    r.organicPage || '',
    r.organicPosition || '',
    r.adPage || '',
    r.adPosition || '',
    r.status,
    r.timestamp,
  ]);
  
  // 转换为 CSV 格式
  const csvContent = [
    headers.join(','),
    ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
  ].join('\n');
  
  // 创建下载链接
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `asin_ranker_results_${new Date().getTime()}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  ElMessage.success('导出成功');
};
</script>

<style scoped>
.result-table-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rank-found {
  color: #67c23a;
  font-weight: 500;
}

.rank-not-found {
  color: #909399;
}

.statistics {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.stat-success {
  color: #67c23a;
  font-weight: 600;
}

.stat-error {
  color: #f56c6c;
  font-weight: 600;
}

.stat-warning {
  color: #e6a23c;
  font-weight: 600;
}

.rate-text {
  margin-left: 8px;
  font-weight: 600;
  color: #67c23a;
}
</style>
