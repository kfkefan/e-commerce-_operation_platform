<template>
  <div class="home-page">
    <el-row :gutter="20">
      <!-- 左侧：任务输入和进度 -->
      <el-col :span="12">
        <!-- 任务输入组件 -->
        <TaskInput @submitted="handleTaskSubmitted" />
        
        <!-- 任务进度组件 -->
        <TaskProgress
          v-if="currentTask"
          :task="currentTask"
          @cancelled="handleTaskCancelled"
          @view-results="handleViewResults"
          @refresh="refreshCurrentTask"
        />
      </el-col>
      
      <!-- 右侧：任务列表和结果 -->
      <el-col :span="12">
        <!-- 任务列表 -->
        <el-card class="task-list-card">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <span>任务列表</span>
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
              <el-button
                type="primary"
                size="small"
                :loading="loadingList"
                @click="loadTaskList(true)"
              >
                刷新
              </el-button>
            </div>
          </template>
          
          <el-table
            :data="taskList"
            style="width: 100%"
            stripe
            highlight-current-row
            v-loading="loadingList"
            @row-click="handleRowClick"
          >
            <el-table-column prop="taskId" label="任务 ID" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="totalKeywords" label="关键词数" width="80" align="center" />
            <el-table-column prop="createdAt" label="创建时间" width="160" align="center">
              <template #default="{ row }">
                {{ formatDate(row.createdAt) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <!-- 任务结果 -->
        <ResultTable
          v-if="showResults && currentResults"
          :results="currentResults"
          :loading="loadingResults"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Loading } from '@element-plus/icons-vue';
import TaskInput from '../components/TaskInput.vue';
import TaskProgress from '../components/TaskProgress.vue';
import ResultTable from '../components/ResultTable.vue';
import { getTaskList, getTaskDetail, getTaskResults } from '../api/tasks';
import type { TaskDetail, TaskListItem, RankingResult } from '../types';

// 任务列表
const taskList = ref<TaskListItem[]>([]);
const loadingList = ref(false);

// 当前任务
const currentTask = ref<TaskDetail | null>(null);

// 任务结果
const currentResults = ref<RankingResult[]>([]);
const loadingResults = ref(false);
const showResults = ref(false);

// 自动刷新控制
const autoRefreshInterval = ref<NodeJS.Timeout | null>(null);
const REFRESH_INTERVAL = 3000; // 3 秒刷新一次

// 检查是否有运行中的任务（pending 或 running 状态）
const hasRunningTasks = computed(() => {
  return taskList.value.some(task => 
    task.status === 'running' || task.status === 'pending'
  );
});

// 检查当前任务是否已完成
const isCurrentTaskCompleted = computed(() => {
  return currentTask.value?.status === 'completed' || 
         currentTask.value?.status === 'failed' || 
         currentTask.value?.status === 'cancelled';
});

// 加载任务列表
const loadTaskList = async (showMessage: boolean = false) => {
  loadingList.value = true;
  
  try {
    const response = await getTaskList({ page: 1, pageSize: 5 });
    const oldList = taskList.value;
    taskList.value = response.tasks;
    
    // 只有当前任务未完成时才同步更新详情
    if (currentTask.value && !isCurrentTaskCompleted.value) {
      const updatedTask = response.tasks.find(t => t.taskId === currentTask.value?.taskId);
      if (updatedTask && updatedTask.status !== currentTask.value.status) {
        await loadTaskDetail(currentTask.value.taskId);
      }
    }
    
    // 检测任务状态变化（仅在有运行中任务时提示）
    if (showMessage && oldList.length > 0 && hasRunningTasks.value) {
      const completedCount = response.tasks.filter(t => t.status === 'completed').length - 
                            oldList.filter(t => t.status === 'completed').length;
      if (completedCount > 0) {
        ElMessage.success(`有 ${completedCount} 个任务已完成`);
      }
    }
  } catch (error: any) {
    if (showMessage) {
      ElMessage.error('加载任务列表失败');
    }
  } finally {
    loadingList.value = false;
  }
};

// 启动自动刷新
const startAutoRefresh = () => {
  stopAutoRefresh(); // 先停止之前的
  
  autoRefreshInterval.value = setInterval(() => {
    if (hasRunningTasks.value) {
      loadTaskList(false); // 静默刷新
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

// 处理任务提交
const handleTaskSubmitted = async (taskId: string) => {
  // 加载任务详情
  await loadTaskDetail(taskId);
  // 刷新列表
  await loadTaskList();
};

// 加载任务详情
const loadTaskDetail = async (taskId: string) => {
  try {
    const detail = await getTaskDetail(taskId);
    currentTask.value = detail;
    
    // 如果任务已完成且尚未显示结果，自动加载结果
    if (detail.status === 'completed' && !showResults.value) {
      await loadTaskResults(taskId);
    }
  } catch (error: any) {
    ElMessage.error('加载任务详情失败');
  }
};

// 刷新当前任务
const refreshCurrentTask = async () => {
  if (currentTask.value) {
    await loadTaskDetail(currentTask.value.taskId);
  }
};

// 处理任务取消
const handleTaskCancelled = (taskId: string) => {
  currentTask.value = null;
  loadTaskList();
};

// 查看结果
const handleViewResults = async () => {
  if (currentTask.value) {
    await loadTaskResults(currentTask.value.taskId);
  }
};

// 加载任务结果
const loadTaskResults = async (taskId: string) => {
  loadingResults.value = true;
  showResults.value = true;
  currentResults.value = [];  // 清空旧数据
  
  try {
    const response = await getTaskResults(taskId);
    currentResults.value = response.results || [];
    
    // 确保加载状态被正确清除
    setTimeout(() => {
      loadingResults.value = false;
    }, 100);
  } catch (error: any) {
    ElMessage.error('加载任务结果失败：' + (error.message || '未知错误'));
    loadingResults.value = false;
  }
};

// 处理行点击
const handleRowClick = (row: TaskListItem) => {
  loadTaskDetail(row.taskId);
  showResults.value = false;
};

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

// 格式化日期
const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// 生命周期
onMounted(() => {
  loadTaskList();
  startAutoRefresh(); // 启动自动刷新
});

// 组件卸载时清理
onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.home-page {
  padding: 10px;
}

.task-list-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.auto-refresh-tag {
  margin-left: 8px;
}
</style>
