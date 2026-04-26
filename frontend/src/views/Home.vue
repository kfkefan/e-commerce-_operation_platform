<template>
  <div class="home-page">
    <el-row :gutter="20" class="content-row">
      <!-- 左侧：任务输入和进度 (1/3 宽度) -->
      <el-col :span="8" :xs="24" :sm="24" :md="8" class="left-col">
        <!-- 任务输入组件 -->
        <TaskInput 
          @submitted="handleTaskSubmitted" 
          @refresh-history="refreshHistoryList"
        />
        
        <!-- 任务进度组件 -->
        <TaskProgress
          v-if="currentTask"
          :task="currentTask"
          @cancelled="handleTaskCancelled"
          @view-results="handleViewResults"
          @refresh="refreshCurrentTask"
          @retried="handleTaskRetried"
        />
        
        <!-- 趋势分析图 -->
        <TrendAnalysis
          v-if="showTrend && currentTask"
          :task-id="currentTask.taskId"
          :asin="currentTask.asin"
        />
      </el-col>
      
      <!-- 右侧：任务列表和结果 (2/3 宽度) -->
      <el-col :span="16" :xs="24" :sm="24" :md="16" class="right-col">
        <!-- 任务结果 -->
        <ResultTable
          v-if="showResults && currentResults"
          :results="currentResults"
          :loading="loadingResults"
        />
        
        <!-- 历史任务列表 -->
        <TaskHistory
          :refresh-trigger="historyRefreshTrigger"
          @view-results="handleViewResultsFromHistory"
          @retry-task="handleTaskRetried"
          @select-task="handleSelectTask"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import TaskInput from '../components/TaskInput.vue';
import TaskProgress from '../components/TaskProgress.vue';
import ResultTable from '../components/ResultTable.vue';
import TaskHistory from '../components/TaskHistory.vue';
import TrendAnalysis from '../components/TrendAnalysis.vue';
import { getTaskDetail, getTaskResults, getTaskList } from '../api/tasks';
import type { TaskDetail, TaskListItem, RankingResult } from '../types';

// 当前任务
const currentTask = ref<TaskDetail | null>(null);

// 任务结果
const currentResults = ref<RankingResult[]>([]);
const loadingResults = ref(false);
const showResults = ref(false);

// 趋势图
const showTrend = ref(false);

// 当前关键词列表（用于预置结果）
const currentKeywords = ref<string[]>([]);

// 历史列表刷新触发器
const historyRefreshTrigger = ref(0);

// 页面初始化时加载最近完成的任务
onMounted(async () => {
  await loadLatestCompletedTask();
});

// 刷新历史列表
const refreshHistoryList = () => {
  historyRefreshTrigger.value += 1;
};

// 处理任务提交
const handleTaskSubmitted = async (taskId: string, keywords?: string[]) => {
  await loadTaskDetail(taskId);
  
  // 如果有关键词，立即创建预制结果
  if (keywords && keywords.length > 0) {
    createPresetResults(keywords);
  }
};

// 创建预制结果（任务刚开始时显示）
const createPresetResults = (keywords: string[]) => {
  currentKeywords.value = keywords;
  
  // 为每个关键词创建占位数据
  const presetResults: RankingResult[] = keywords.map(keyword => ({
    keyword,
    organicPage: null,
    organicPosition: null,
    adPage: null,
    adPosition: null,
    status: 'pending' as any, // 待爬取状态
    timestamp: new Date().toISOString(),
  }));
  
  currentResults.value = presetResults;
  showResults.value = true;
  loadingResults.value = false;
};

// 加载任务详情
const loadTaskDetail = async (taskId: string) => {
  try {
    const detail = await getTaskDetail(taskId);
    currentTask.value = detail;
    showTrend.value = true;
    
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
    
    // 如果任务完成了，自动加载结果
    if (currentTask.value.status === 'completed') {
      await loadTaskResults(currentTask.value.taskId);
      showResults.value = true;
    }
  }
};

// 处理任务取消
const handleTaskCancelled = (taskId: string) => {
  currentTask.value = null;
  showTrend.value = false;
};

// 处理任务重试
const handleTaskRetried = (newTaskId: string) => {
  loadTaskDetail(newTaskId);
};

// 查看结果
const handleViewResults = async () => {
  if (currentTask.value) {
    await loadTaskResults(currentTask.value.taskId);
  }
};

// 从历史列表查看结果
const handleViewResultsFromHistory = (taskId: string) => {
  loadTaskDetail(taskId);
  showResults.value = true;
};

// 选择任务
const handleSelectTask = (task: TaskListItem) => {
  loadTaskDetail(task.taskId);
  showResults.value = false;
};

// 加载任务结果
const loadTaskResults = async (taskId: string) => {
  loadingResults.value = true;
  showResults.value = true;
  currentResults.value = [];
  
  try {
    const response = await getTaskResults(taskId);
    currentResults.value = response.results || [];
    
    setTimeout(() => {
      loadingResults.value = false;
    }, 100);
  } catch (error: any) {
    ElMessage.error('加载任务结果失败：' + (error.message || '未知错误'));
    loadingResults.value = false;
  }
};

// 加载最近完成的任务
const loadLatestCompletedTask = async () => {
  try {
    // 获取最近的任务列表（只取第一个）
    const response = await getTaskList({ page: 1, pageSize: 1 });
    const tasks = response.tasks;
    
    if (tasks && tasks.length > 0) {
      const latestTask = tasks[0];
      
      // 如果最近任务是已完成状态，显示它的结果
      if (latestTask.status === 'completed') {
        await loadTaskDetail(latestTask.taskId);
        await loadTaskResults(latestTask.taskId);
        showTrend.value = true;
      } else {
        // 否则只显示任务详情（进度等），但不显示结果
        await loadTaskDetail(latestTask.taskId);
        showTrend.value = true;
      }
    }
  } catch (error) {
    console.log('加载最近任务失败:', error);
    // 失败不报错，静默处理
  }
};
</script>

<style scoped>
.home-page {
  padding: 20px;
  min-height: 100vh;
}

.content-row {
  display: flex;
  flex-direction: column;
}

@media (min-width: 768px) {
  .content-row {
    flex-direction: row;
  }
}

.left-col,
.right-col {
  margin-bottom: 24px;
}

@media (max-width: 767px) {
  .left-col,
  .right-col {
    margin-bottom: 16px;
  }
}
</style>
