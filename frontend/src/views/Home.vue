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
              <span>任务列表</span>
              <el-button
                type="primary"
                size="small"
                :loading="loadingList"
                @click="loadTaskList"
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
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
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

// 加载任务列表
const loadTaskList = async () => {
  loadingList.value = true;
  
  try {
    const response = await getTaskList({ page: 1, pageSize: 10 });
    taskList.value = response.tasks;
  } catch (error: any) {
    ElMessage.error('加载任务列表失败');
  } finally {
    loadingList.value = false;
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
    
    // 如果任务已完成，自动加载结果
    if (detail.status === 'completed') {
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
  
  try {
    const response = await getTaskResults(taskId);
    currentResults.value = response.results;
  } catch (error: any) {
    ElMessage.error('加载任务结果失败');
  } finally {
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
</style>
