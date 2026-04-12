import { useState, useCallback, useEffect } from 'react';
import { createTask, getTaskDetail, pauseTask, resumeTask, cancelTask, getTaskResults } from '../api/tasks';
import type { CreateTaskParams, TaskDetail, RankResult } from '../api/tasks';

/**
 * 任务管理 Hook
 * 负责任务的创建、查询、状态更新等操作
 */
export function useTask(taskId?: string) {
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * 创建任务
   */
  const create = useCallback(async (params: CreateTaskParams) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await createTask(params);
      setTask({
        taskId: response.taskId,
        status: response.status,
        asin: params.asin,
        site: params.site || 'amazon.com',
        totalKeywords: params.keywords.length,
        processedKeywords: 0,
        progressPercentage: 0,
        createdAt: new Date().toISOString(),
        estimatedRemainingSeconds: params.keywords.length * 5
      });
      return response.taskId;
    } catch (err: any) {
      const message = err.response?.data?.message || '创建任务失败';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 获取任务详情
   */
  const fetchTask = useCallback(async () => {
    if (!taskId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await getTaskDetail(taskId);
      setTask(data);
    } catch (err: any) {
      const message = err.response?.data?.message || '获取任务详情失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  /**
   * 暂停任务
   */
  const pause = useCallback(async () => {
    if (!taskId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await pauseTask(taskId);
      await fetchTask();
    } catch (err: any) {
      const message = err.response?.data?.message || '暂停任务失败';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [taskId, fetchTask]);

  /**
   * 继续任务
   */
  const resume = useCallback(async () => {
    if (!taskId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await resumeTask(taskId);
      await fetchTask();
    } catch (err: any) {
      const message = err.response?.data?.message || '继续任务失败';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [taskId, fetchTask]);

  /**
   * 取消任务
   */
  const cancel = useCallback(async () => {
    if (!taskId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await cancelTask(taskId);
      await fetchTask();
    } catch (err: any) {
      const message = err.response?.data?.message || '取消任务失败';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [taskId, fetchTask]);

  /**
   * 获取任务结果
   */
  const fetchResults = useCallback(async (options?: {
    page?: number;
    pageSize?: number;
    status?: string;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }) => {
    if (!taskId) return { results: [], pagination: { page: 1, pageSize: 50, total: 0, totalPages: 0 } };
    
    setLoading(true);
    setError(null);
    
    try {
      return await getTaskResults(taskId, options);
    } catch (err: any) {
      const message = err.response?.data?.message || '获取任务结果失败';
      setError(message);
      return { results: [], pagination: { page: 1, pageSize: 50, total: 0, totalPages: 0 } };
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  return {
    task,
    loading,
    error,
    create,
    fetchTask,
    pause,
    resume,
    cancel,
    fetchResults
  };
}

/**
 * 任务轮询 Hook
 * 定期轮询任务状态
 */
export function useTaskPolling(taskId: string | null, intervalMs: number = 3000) {
  const { task, fetchTask } = useTask(taskId || undefined);
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    if (!taskId || !isPolling) return;

    // 立即获取一次
    fetchTask();

    // 定时轮询
    const timer = setInterval(() => {
      fetchTask();
      
      // 如果任务已完成或失败，停止轮询
      if (task && (task.status === 'completed' || task.status === 'failed')) {
        setIsPolling(false);
        clearInterval(timer);
      }
    }, intervalMs);

    return () => {
      clearInterval(timer);
    };
  }, [taskId, isPolling, fetchTask, task?.status]);

  return {
    task,
    isPolling,
    setIsPolling,
    refresh: fetchTask
  };
}
