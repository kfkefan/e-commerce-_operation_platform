<template>
  <el-card class="task-history-card">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span>历史任务</span>
          <el-tag 
            v-if="hasRunningTasks" 
            type="warning" 
            size="small" 
            effect="plain"
            class="auto-refresh-tag"
          >
            <el-icon class="is-loading"><Loading /></el-icon>
            自动刷新中
          </el-tag>
        </div>
        <div class="header-actions">
          <!-- ASIN 搜索 -->
          <el-input
            v-model="searchAsin"
            placeholder="搜索 ASIN"
            prefix-icon="Search"
            size="small"
            clearable
            style="width: 200px;"
            @keyup.enter="handleSearch"
          />
          <!-- 刷新按钮 -->
          <el-button
            type="primary"
            size="small"
            :loading="loading"
            @click="loadHistory(false)"
          >
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </template>
    
    <!-- 任务列表表格 -->
    <el-table
      :data="taskList"
      style="width: 100%"
      border
      stripe
      v-loading="loading"
      :height="400"
      @row-click="handleRowClick"
    >
      <!-- 任务 ID -->
      <el-table-column
        prop="taskId"
        label="任务 ID"
        min-width="280"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <span class="task-id">{{ formatTaskId(row.taskId) }}</span>
        </template>
      </el-table-column>
      
      <!-- ASIN -->
      <el-table-column
        prop="asin"
        label="ASIN"
        width="120"
        align="center"
        sortable
      >
        <template #default="{ row }">
          <span class="asin-text">{{ row.asin }}</span>
        </template>
      </el-table-column>
      
      <!-- 状态 -->
      <el-table-column
        prop="status"
        label="状态"
        width="100"
        align="center"
        sortable
      >
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <!-- 关键词数 -->
      <el-table-column
        prop="totalKeywords"
        label="关键词数"
        width="90"
        align="center"
        sortable
      />
      
      <!-- 进度 -->
      <el-table-column
        label="进度"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <el-progress
            :percentage="getProgress(row)"
            :status="row.status === 'failed' ? 'exception' : undefined"
            :stroke-width="12"
          />
        </template>
      </el-table-column>
      
      <!-- 提交时间 -->
      <el-table-column
        prop="createdAt"
        label="提交时间"
        width="160"
        sortable
        align="center"
      >
        <template #default="{ row }">
          <span class="time-text">{{ formatDate(row.createdAt) }}</span>
        </template>
      </el-table-column>
      
      <!-- 完成时间 -->
      <el-table-column
        prop="completedAt"
        label="完成时间"
        width="160"
        sortable
        align="center"
      >
        <template #default="{ row }">
          <span v-if="row.completedAt" class="time-text">
            {{ formatDate(row.completedAt) }}
          </span>
          <span v-else class="time-text-empty">-</span>
        </template>
      </el-table-column>
      
      <!-- 操作 -->
      <el-table-column
        label="操作"
        width="120"
        align="center"
        fixed="right"
      >
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'completed'"
            type="primary"
            size="small"
            @click.stop="handleViewResults(row)"
          >
            查看结果
          </el-button>
          <el-button
            v-else-if="row.canRetry"
            type="warning"
            size="small"
            @click.stop="handleRetry(row)"
          >
            重试
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { Search, Refresh, Loading } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { getTaskList, retryTask } from '../api/tasks';
import type { TaskListItem } from '../types';

// 定义 emits
const emit = defineEmits<{
  (e: 'view-results', taskId: string): void;
  (e: 'retry-task', taskId: string): void;
  (e: 'select-task', task: TaskListItem): void;
}>();

// 任务列表
const taskList = ref<TaskListItem[]>([]);
const loading = ref(false);

// 分页
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

// 搜索
const searchAsin = ref('');

// 自动刷新控制
const autoRefreshInterval = ref<NodeJS.Timeout | null>(null);
const REFRESH_INTERVAL = 5000; // 5 秒刷新一次

// 检查是否有运行中的任务
const hasRunningTasks = computed(() => {
  return taskList.value.some(task => 
    task.status === 'running' || task.status === 'pending' || task.status === 'retrying'
  );
});

// 加载历史任务
const loadHistory = async (silent: boolean = false) => {
  if (!silent) {
    loading.value = true;
  }
  
  try {
    const response = await getTaskList({
      page: currentPage.value,
      pageSize: pageSize.value,
      asin: searchAsin.value || undefined, // 传入搜索条件
    });
    
    taskList.value = response.tasks;
    total.value = response.pagination.total;
  } catch (error: any) {
    if (!silent) {
      ElMessage.error('加载历史任务失败');
    }
  } finally {
    if (!silent) {
      loading.value = false;
    }
  }
};

// 启动自动刷新
const startAutoRefresh = () => {
  stopAutoRefresh(); // 先停止之前的
  
  autoRefreshInterval.value = setInterval(() => {
    if (hasRunningTasks.value) {
      loadHistory(true); // 静默刷新
    }
  }, REFRESH_INTERVAL);
};

// 停止自动刷新
const stopAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value);
    autoRefreshInterval.value = null;
  }
};

// 搜索
const handleSearch = () => {
  currentPage.value = 1;
  loadHistory();
};

// 分页变化
const handleSizeChange = () => {
  currentPage.value = 1;
  loadHistory();
};

const handlePageChange = () => {
  loadHistory();
};

// 格式化任务 ID（显示缩略）
const formatTaskId = (taskId: string) => {
  if (taskId.length <= 16) return taskId;
  return `${taskId.slice(0, 8)}...${taskId.slice(-8)}`;
};

// 获取进度
const getProgress = (row: TaskListItem) => {
  if (row.status === 'completed') return 100;
  if (row.status === 'failed' || row.status === 'cancelled') return 0;
  if (row.totalKeywords === 0) return 0;
  return Math.round((row.processedKeywords / row.totalKeywords) * 100);
};

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
    retrying: 'warning',
  };
  return types[status] || 'info';
};

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    retrying: '等待重试',
  };
  return texts[status] || status;
};

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// 行点击
const handleRowClick = (row: TaskListItem) => {
  emit('select-task', row);
};

// 查看结果
const handleViewResults = (row: TaskListItem) => {
  emit('view-results', row.taskId);
};

// 重试任务
const handleRetry = async (row: TaskListItem) => {
  try {
    const response = await retryTask(row.taskId);
    ElMessage.success(`重试任务已创建：${formatTaskId(response.taskId)}`);
    emit('retry-task', response.taskId);
    loadHistory();
  } catch (error: any) {
    const message = error.response?.data?.message || '重试失败';
    ElMessage.error(message);
  }
};

// 生命周期
onMounted(() => {
  loadHistory();
  startAutoRefresh(); // 启动自动刷新
});

// 组件卸载时清理
onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.task-history-card {
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

.task-id {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #606266;
}

.asin-text {
  font-weight: 600;
  color: #409EFF;
}

.time-text {
  font-size: 13px;
  color: #909399;
}

.time-text-empty {
  color: #DCDFE6;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
