/**
 * TypeScript 类型定义
 */

// ========== 枚举类型 ==========

export type TaskStatus = 
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type RankingStatus =
  | 'found'
  | 'organic_not_found'
  | 'ad_not_found'
  | 'not_found'
  | 'error'
  | 'captcha';

// ========== 请求模型 ==========

export interface TaskCreateRequest {
  asin: string;
  keywords: string[];
  maxPages?: number;
  site?: string;
}

// ========== 响应模型 ==========

export interface TaskResponse {
  taskId: string;
  status: TaskStatus;
  createdAt: string;
  totalKeywords?: number;
  maxPages?: number;
}

export interface TaskDetail {
  taskId: string;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
  asin: string;
  site: string;
  maxPages: number;
  totalKeywords: number;
  processedKeywords: number;
  progress: number;
  errorMessage?: string | null;
}

export interface TaskListItem {
  taskId: string;
  status: TaskStatus;
  createdAt: string;
  completedAt?: string | null;
  totalKeywords: number;
  processedKeywords: number;
}

export interface Pagination {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface TaskListResponse {
  tasks: TaskListItem[];
  pagination: Pagination;
}

export interface RankingResult {
  keyword: string;
  organicPage: number | null;
  organicPosition: number | null;
  adPage: number | null;
  adPosition: number | null;
  status: RankingStatus;
  timestamp: string;
}

export interface TaskResultsResponse {
  taskId: string;
  asin: string;
  site: string;
  completedAt?: string | null;
  results: RankingResult[];
}

// ========== 错误模型 ==========

export interface ErrorResponse {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// ========== API 响应 ==========

export interface ApiResponse<T> {
  data?: T;
  error?: ErrorResponse;
}
