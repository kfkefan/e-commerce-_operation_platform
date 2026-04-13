/**
 * API 调用封装
 */
import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  TaskCreateRequest,
  TaskResponse,
  TaskDetail,
  TaskListResponse,
  TaskResultsResponse,
  ErrorResponse,
} from '../types';

// API 基础 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError<ErrorResponse>) => {
    // 统一错误处理
    if (error.response) {
      const errorData = error.response.data;
      console.error('API Error:', errorData);
    }
    return Promise.reject(error);
  }
);

// ========== 任务相关 API ==========

/**
 * 创建任务
 */
export async function createTask(request: TaskCreateRequest): Promise<TaskResponse> {
  const response = await apiClient.post<TaskResponse>('/tasks', request);
  return response.data;
}

/**
 * 获取任务列表
 */
export async function getTaskList(params?: {
  status?: string;
  page?: number;
  pageSize?: number;
}): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>('/tasks', { params });
  return response.data;
}

/**
 * 获取任务详情
 */
export async function getTaskDetail(taskId: string): Promise<TaskDetail> {
  const response = await apiClient.get<TaskDetail>(`/tasks/${taskId}`);
  return response.data;
}

/**
 * 取消任务
 */
export async function cancelTask(taskId: string): Promise<TaskResponse> {
  const response = await apiClient.delete<TaskResponse>(`/tasks/${taskId}`);
  return response.data;
}

/**
 * 获取任务结果
 */
export async function getTaskResults(taskId: string): Promise<TaskResultsResponse> {
  const response = await apiClient.get<TaskResultsResponse>(`/tasks/${taskId}/results`);
  return response.data;
}

/**
 * 重试任务
 */
export async function retryTask(taskId: string): Promise<TaskResponse> {
  const response = await apiClient.post<TaskResponse>(`/tasks/${taskId}/retry`);
  return response.data;
}

/**
 * 放弃任务
 */
export async function abandonTask(taskId: string): Promise<TaskResponse> {
  const response = await apiClient.post<TaskResponse>(`/tasks/${taskId}/abandon`);
  return response.data;
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{
  status: string;
  version: string;
  timestamp: string;
  checks: {
    database: string;
    crawler: string;
  };
}> {
  const response = await apiClient.get('/health');
  return response.data;
}
