<template>
  <el-card class="task-progress-card">
    <template #header>
      <div class="card-header">
        <span>任务进度</span>
        <el-tag v-if="task" :type="getStatusType(task.status)">
          {{ getStatusText(task.status) }}
        </el-tag>
      </div>
    </template>
    
    <div v-if="task" class="progress-content">
      <!-- 任务信息 -->
      <div class="task-info">
        <div class="info-item">
          <span class="label">ASIN:</span>
          <span class="value">{{ task.asin }}</span>
        </div>
        <div class="info-item">
          <span class="label">站点:</span>
          <span class="value">{{ task.site }}</span>
        </div>
        <div class="info-item">
          <span class="label">创建时间:</span>
          <span class="value">{{ formatDate(task.createdAt) }}</span>
        </div>
      </div>
      
      <!-- 进度条 -->
      <div class="progress-bar">
        <el-progress
          :percentage="task.progress"
          :status="getProgressStatus(task.status)"
          :stroke-width="20"
        >
          <template #default="{ percentage }">
            <span class="progress-text">{{ percentage }}%</span>
            <span class="progress-detail">
              ({{ task.processedKeywords }}/{{ task.totalKeywords }})
            </span>
          </template>
        </el-progress>
      </div>
      
      <!-- 错误信息 -->
      <el-alert
        v-if="task.errorMessage"
        type="error"
        :title="task.errorMessage"
        show-icon
        closable
      />
      
      <!-- 操作按钮 -->
      <div class="actions">
        <el-button
          v-if="task.status === 'running' || task.status === 'pending'"
          type="danger"
          size="small"
          :loading="cancelling"
          @click="handleCancel"
        >
          取消任务
        </el-button>
        <el-button
          v-if="task.status === 'completed'"
          type="success"
          size="small"
          @click="$emit('view-results')"
        >
          查看结果
        </el-button>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <el-empty description="暂无任务" />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import type { TaskDetail } from '../types';
import { cancelTask as apiCancelTask } from '../api/tasks';
import { ElMessage, ElMessageBox } from 'element-plus';

// 定义 props
const props = defineProps<{
  task: TaskDetail | null;
}>();

// 定义 emits
const emit = defineEmits<{
  (e: 'cancelled', taskId: string): void;
  (e: 'view-results'): void;
  (e: 'refresh'): void;
}>();

// 取消状态
const cancelling = ref(false);

// 自动刷新定时器
let refreshInterval: NodeJS.Timeout | null = null;

// 启动自动刷新（仅当任务运行中）
const startAutoRefresh = () => {
  stopAutoRefresh(); // 先停止之前的
  
  if (props.task && (props.task.status === 'running' || props.task.status === 'pending')) {
    refreshInterval = setInterval(() => {
      // 每次都检查最新状态
      if (props.task && (props.task.status === 'running' || props.task.status === 'pending')) {
        emit('refresh');
      } else {
        stopAutoRefresh();
      }
    }, 5000);
  }
};

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
};

// 监听任务变化，启动/停止自动刷新
watch(
  () => props.task?.status,
  (newStatus) => {
    if (newStatus === 'running' || newStatus === 'pending') {
      startAutoRefresh();
    } else {
      stopAutoRefresh();
    }
  },
  { immediate: true }
);

// 组件卸载时清理
onUnmounted(() => {
  stopAutoRefresh();
});

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
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
  };
  return texts[status] || status;
};

// 获取进度条状态
const getProgressStatus = (status: string) => {
  if (status === 'completed') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'exception';
  return undefined;
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
  });
};

// 取消任务
const handleCancel = async () => {
  if (!props.task) return;
  
  try {
    await ElMessageBox.confirm('确定要取消该任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    
    cancelling.value = true;
    await apiCancelTask(props.task.taskId);
    ElMessage.success('任务已取消');
    emit('cancelled', props.task.taskId);
    emit('refresh');
  } catch (error: any) {
    if (error !== 'cancel') {
      const message = error.response?.data?.message || '取消失败';
      ElMessage.error(message);
    }
  } finally {
    cancelling.value = false;
  }
};
</script>

<style scoped>
.task-progress-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-content {
  padding: 10px 0;
}

.task-info {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.info-item {
  text-align: center;
}

.info-item .label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.info-item .value {
  display: block;
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.progress-bar {
  margin: 20px 0;
}

.progress-text {
  font-weight: 600;
  font-size: 14px;
}

.progress-detail {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 15px;
}

.empty-state {
  padding: 20px 0;
}
</style>
