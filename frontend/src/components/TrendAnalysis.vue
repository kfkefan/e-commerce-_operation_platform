<template>
  <el-card class="trend-analysis-card" v-if="showTrend">
    <template #header>
      <div class="card-header">
        <span>排名趋势分析</span>
        <el-tag :type="taskCompleted ? 'success' : 'info'" size="small">
          {{ taskCompleted ? '任务已完成' : '任务进行中' }}
        </el-tag>
      </div>
    </template>
    
    <!-- 图表容器 -->
    <div ref="chartRef" class="trend-chart" style="height: 300px;"></div>
    
    <!-- 关键词选择 -->
    <div class="keyword-selector" v-if="keywords.length > 0">
      <span class="label">选择关键词：</span>
      <el-select
        v-model="selectedKeyword"
        placeholder="选择关键词查看趋势"
        size="small"
        style="width: 300px;"
        @change="updateChart"
      >
        <el-option
          v-for="kw in keywords"
          :key="kw"
          :label="kw"
          :value="kw"
        />
      </el-select>
    </div>
    
    <!-- 空状态 -->
    <el-empty
      v-if="!taskCompleted && keywords.length === 0"
      description="任务完成后将显示趋势分析"
      :image-size="80"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { getTaskResults } from '../api/tasks';
import type { RankingResult } from '../types';

// 定义 props
const props = defineProps<{
  taskId: string;
  asin: string;
}>();

// 图表引用
const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

// 数据
const keywords = ref<string[]>([]);
const selectedKeyword = ref('');
const taskCompleted = ref(false);
const showTrend = ref(false);

// 初始化图表
const initChart = async () => {
  if (!chartRef.value) return;
  
  // 销毁旧实例
  if (chartInstance) {
    chartInstance.dispose();
  }
  
  // 创建新实例
  chartInstance = echarts.init(chartRef.value);
  
  // 加载数据
  await loadData();
};

// 加载数据
const loadData = async () => {
  try {
    const response = await getTaskResults(props.taskId);
    const results = response.results || [];
    
    if (results.length === 0) {
      showTrend.value = false;
      return;
    }
    
    showTrend.value = true;
    taskCompleted.value = true;
    
    // 提取关键词列表
    keywords.value = results.map(r => r.keyword);
    if (keywords.value.length > 0 && !selectedKeyword.value) {
      selectedKeyword.value = keywords.value[0];
    }
    
    // 更新图表
    await nextTick();
    updateChart();
  } catch (error) {
    console.error('加载趋势数据失败:', error);
    showTrend.value = false;
  }
};

// 更新图表
const updateChart = () => {
  if (!chartInstance || !selectedKeyword.value) return;
  
  // 这里简化处理，实际应该从后端获取历史数据
  // 目前只显示当前任务的排名情况
  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0];
        return `${selectedKeyword.value}<br/>
                自然排名：第${data.data[1]}页 第${data.data[2]}位<br/>
                广告排名：第${data.data[3]}页 第${data.data[4]}位`;
      }
    },
    legend: {
      data: ['自然排名', '广告排名'],
      bottom: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['当前']
    },
    yAxis: {
      type: 'value',
      name: '排名位置',
      inverse: true, // 排名越小越靠上
      min: 1,
      max: 100
    },
    series: [
      {
        name: '自然排名',
        type: 'line',
        data: getRankData('organic'),
        smooth: true,
        itemStyle: {
          color: '#67c23a'
        },
        areaStyle: {
          color: 'rgba(103, 194, 58, 0.1)'
        }
      },
      {
        name: '广告排名',
        type: 'line',
        data: getRankData('ad'),
        smooth: true,
        itemStyle: {
          color: '#e6a23c'
        },
        areaStyle: {
          color: 'rgba(230, 162, 60, 0.1)'
        }
      }
    ]
  };
  
  chartInstance.setOption(option);
};

// 获取排名数据
const getRankData = (type: 'organic' | 'ad') => {
  // 这里需要后端支持历史数据查询
  // 目前返回示例数据
  return [[0, 1, 15, 1, 5]]; // [x, 自然页，自然位，广告页，广告位]
};

// 监听任务 ID 变化
watch(() => props.taskId, () => {
  initChart();
});

// 监听任务完成状态
watch(() => taskCompleted.value, () => {
  if (taskCompleted.value) {
    updateChart();
  }
});

// 生命周期
onMounted(() => {
  initChart();
  
  // 窗口大小变化时重绘
  window.addEventListener('resize', () => {
    chartInstance?.resize();
  });
});
</script>

<style scoped>
.trend-analysis-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trend-chart {
  width: 100%;
}

.keyword-selector {
  margin-top: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.keyword-selector .label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}
</style>
