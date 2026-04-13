<template>
  <el-card class="result-table-card">
    <template #header>
      <div class="card-header">
        <span>排名结果</span>
        <div class="header-actions">
          <!-- 筛选 -->
          <el-select
            v-model="filterStatus"
            placeholder="按状态筛选"
            clearable
            size="small"
            style="width: 150px; margin-right: 10px;"
            @change="handleFilter"
          >
            <el-option label="全部状态" value="" />
            <el-option label="已找到" value="found" />
            <el-option label="仅自然未找到" value="organic_not_found" />
            <el-option label="仅广告未找到" value="ad_not_found" />
            <el-option label="未找到" value="not_found" />
            <el-option label="错误" value="error" />
            <el-option label="验证码" value="captcha" />
          </el-select>
          
          <!-- 导出按钮 -->
          <el-button
            type="success"
            size="small"
            :disabled="results.length === 0"
            @click="handleExport"
          >
            <el-icon><Download /></el-icon>
            导出 CSV
          </el-button>
        </div>
      </div>
    </template>
    
    <!-- 结果表格 -->
    <el-table
      :data="filteredResults"
      style="width: 100%"
      border
      stripe
      :default-sort="{ prop: 'keyword', order: 'ascending' }"
      v-loading="loading"
      :height="Math.min(results.length * 55 + 60, 500)"
    >
      <!-- 关键词 -->
      <el-table-column
        prop="keyword"
        label="关键词"
        sortable
        min-width="200"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <span class="keyword-text">{{ row.keyword }}</span>
        </template>
      </el-table-column>
      
      <!-- 自然排名 -->
      <el-table-column
        label="自然排名"
        width="140"
        align="center"
        sortable
        :sort-method="sortNaturalRank"
      >
        <template #default="{ row }">
          <span v-if="row.organicPage && row.organicPosition" class="rank-found">
            <el-tag type="success" size="small">
              第{{ row.organicPage }}页 - 第{{ row.organicPosition }}位
            </el-tag>
          </span>
          <span v-else class="rank-not-found">
            <el-tag type="info" size="small">未找到</el-tag>
          </span>
        </template>
      </el-table-column>
      
      <!-- 广告排名 -->
      <el-table-column
        label="广告排名"
        width="140"
        align="center"
        sortable
        :sort-method="sortAdRank"
      >
        <template #default="{ row }">
          <span v-if="row.adPage && row.adPosition" class="rank-found">
            <el-tag type="warning" size="small">
              第{{ row.adPage }}页 - 第{{ row.adPosition }}位
            </el-tag>
          </span>
          <span v-else class="rank-not-found">
            <el-tag type="info" size="small">未找到</el-tag>
          </span>
        </template>
      </el-table-column>
      
      <!-- 状态 -->
      <el-table-column
        prop="status"
        label="状态"
        width="120"
        align="center"
        sortable
      >
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <!-- 爬取时间 -->
      <el-table-column
        prop="timestamp"
        label="爬取时间"
        width="160"
        sortable
        align="center"
      >
        <template #default="{ row }">
          <span class="timestamp-text">{{ formatDate(row.timestamp) }}</span>
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
import { Download } from '@element-plus/icons-vue';
import type { RankingResult } from '../types';
import { ElMessage } from 'element-plus';

// 定义 props
const props = defineProps<{
  results: RankingResult[];
  loading?: boolean;
}>();

// 筛选状态
const filterStatus = ref('');
const filteredResults = ref<RankingResult[]>([]);

// 初始化筛选结果
filteredResults.value = props.results;

// 监听结果变化
import { watch } from 'vue';
watch(() => props.results, (newResults) => {
  filteredResults.value = newResults;
  handleFilter();
}, { immediate: true });

// 处理筛选
const handleFilter = () => {
  if (!filterStatus.value) {
    filteredResults.value = props.results;
  } else {
    filteredResults.value = props.results.filter(r => r.status === filterStatus.value);
  }
};

// 自然排名排序
const sortNaturalRank = (a: RankingResult, b: RankingResult) => {
  const aRank = a.organicPage && a.organicPosition ? (a.organicPage * 1000 + a.organicPosition) : 999999;
  const bRank = b.organicPage && b.organicPosition ? (b.organicPage * 1000 + b.organicPosition) : 999999;
  return aRank - bRank;
};

// 广告排名排序
const sortAdRank = (a: RankingResult, b: RankingResult) => {
  const aRank = a.adPage && a.adPosition ? (a.adPage * 1000 + a.adPosition) : 999999;
  const bRank = b.adPage && b.adPosition ? (b.adPage * 1000 + b.adPosition) : 999999;
  return aRank - bRank;
};

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
  if (filteredResults.value.length === 0) {
    ElMessage.warning('没有数据可导出');
    return;
  }
  
  // 构建 CSV 内容（带 BOM 防止中文乱码）
  const headers = ['关键词', '自然排名页', '自然排名位置', '广告排名页', '广告排名位置', '状态', '爬取时间'];
  const rows = filteredResults.value.map((r) => [
    r.keyword,
    r.organicPage?.toString() || '',
    r.organicPosition?.toString() || '',
    r.adPage?.toString() || '',
    r.adPosition?.toString() || '',
    getStatusText(r.status),
    formatDate(r.timestamp),
  ]);
  
  // 转换为 CSV 格式
  const csvContent = [
    headers.join(','),
    ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
  ].join('\n');
  
  // 添加 BOM 防止中文乱码
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `ASIN 排名结果_${new Date().getTime()}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  
  ElMessage.success(`已导出 ${filteredResults.value.length} 条记录`);
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
  flex-wrap: wrap;
  gap: 10px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.keyword-text {
  font-weight: 500;
  color: #303133;
}

.rank-found {
  font-weight: 500;
}

.rank-not-found {
  color: #909399;
}

.timestamp-text {
  font-size: 13px;
  color: #606266;
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
