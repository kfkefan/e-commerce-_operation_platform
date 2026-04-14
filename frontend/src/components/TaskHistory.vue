<template>
  <el-card class="task-history-card">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span>历史任务</span>
          <!-- WebSocket 连接状态 -->
          <el-tag 
            :type="wsConnectionStatus === 'connected' ? 'success' : wsConnectionStatus === 'connecting' ? 'warning' : 'info'" 
            size="small" 
            effect="plain"
            class="connection-status-tag"
          >
            <el-icon><connection /></el-icon>
            {{ wsConnectionText }}
          </el-tag>
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
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { Search, Refresh, Loading, Connection } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { getTaskList, retryTask } from '../api/tasks';
import type { TaskListItem } from '../types';

// 定义 emits
const emit = defineEmits<{
  (e: 'view-results', taskId: string): void;
  (e: 'retry-task', taskId: string): void;
  (e: 'select-task', task: TaskListItem): void;
}>();

// 定义 props（用于接收外部刷新信号）
const props = defineProps<{
  refreshTrigger?: number; // 使用数字作为触发器，每次变化都会触发刷新
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
const REFRESH_INTERVAL = 2000; // 2 秒刷新一次，更快响应

// WebSocket 相关
let ws: WebSocket | null = null;
const WS_URL = (() => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  // 从 http://localhost:8000/api/v1 转换为 ws://localhost:8000/ws/tasks
  return baseUrl.replace('/api/v1', '/ws/tasks').replace('http://', 'ws://').replace('https://', 'wss://');
})();
const WS_RECONNECT_DELAY = 3000; // 重连延迟（毫秒）
const wsConnectionStatus = ref<'connected' | 'connecting' | 'disconnected'>('disconnected');

// WebSocket 连接文字
const wsConnectionText = computed(() => {
  const texts = {
    connected: '已连接',
    connecting: '连接中...',
    disconnected: '未连接'
  };
  return texts[wsConnectionStatus.value];
});

// 监听外部刷新触发器
watch(() => props.refreshTrigger, (newVal) => {
  if (newVal !== undefined && newVal !== null) {
    console.log('收到外部刷新信号，立即刷新历史列表');
    loadHistory(false); // 强制刷新
  }
}, { immediate: false });

// 检查是否有运行中的任务
const hasRunningTasks = computed(() => {
  return taskList.value.some(task => 
    task.status === 'running' || task.status === 'pending' || task.status === 'retrying'
  );
});

// WebSocket 连接
const connectWebSocket = () => {
  if (wsConnectionStatus.value === 'connected' || wsConnectionStatus.value === 'connecting') {
    return;
  }

  wsConnectionStatus.value = 'connecting';
  
  try {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      wsConnectionStatus.value = 'connected';
      console.log('WebSocket 已连接');
      ElMessage.success('实时推送已连接');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('收到 WebSocket 消息:', message);
        
        // 处理任务状态更新消息
        if (message.type === 'task_status_update') {
          // 找到对应的任务并更新状态
          const index = taskList.value.findIndex(t => t.taskId === message.task_id);
          if (index !== -1) {
            // 更新任务状态
            taskList.value[index].status = message.status;
            
            // 如果有进度数据也更新
            if (message.processed_keywords !== undefined) {
              taskList.value[index].processedKeywords = message.processed_keywords;
            }
            if (message.total_keywords !== undefined) {
              taskList.value[index].totalKeywords = message.total_keywords;
            }
            
            console.log(`任务 ${message.task_id} 状态更新为：${message.status}`);
            
            // 如果任务已完成或失败，可能需要刷新完整列表获取最新数据
            if (message.status === 'completed' || message.status === 'failed') {
              loadHistory(true);
            }
          } else {
            // 如果当前列表中没有该任务，可能在新的一页，刷新整个列表
            console.log(`任务 ${message.task_id} 不在当前页面，刷新列表`);
            loadHistory(true);
          }
        }
      } catch (error) {
        console.error('解析 WebSocket 消息失败:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
      wsConnectionStatus.value = 'disconnected';
    };

    ws.onclose = (event) => {
      console.log('WebSocket 断开连接:', event.code, event.reason);
      wsConnectionStatus.value = 'disconnected';
      
      // 尝试重连
      setTimeout(() => {
        console.log('尝试重连 WebSocket...');
        connectWebSocket();
      }, WS_RECONNECT_DELAY);
    };

  } catch (error) {
    console.error('创建 WebSocket 失败:', error);
    wsConnectionStatus.value = 'disconnected';
    
    // 稍后重试
    setTimeout(() => {
      connectWebSocket();
    }, WS_RECONNECT_DELAY);
  }
};

// 关闭 WebSocket 连接
const closeWebSocket = () => {
  if (ws) {
    ws.close();
    ws = null;
  }
};

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
  connectWebSocket(); // 建立 WebSocket 连接
});

// 组件卸载时清理
onUnmounted(() => {
  stopAutoRefresh();
  closeWebSocket();
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

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.connection-status-tag {
  font-size: 12px;
}

.auto-refresh-tag {
  font-size: 12px;
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
