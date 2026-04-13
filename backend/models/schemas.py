"""
Pydantic 数据模型
用于请求/响应验证和序列化
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ========== 枚举类型 ==========

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"  # 等待自动重试


class RankingStatus(str, Enum):
    """排名结果状态枚举"""
    FOUND = "found"
    ORGANIC_NOT_FOUND = "organic_not_found"
    AD_NOT_FOUND = "ad_not_found"
    NOT_FOUND = "not_found"
    ERROR = "error"
    CAPTCHA = "captcha"


# ========== 请求模型 ==========

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    asin: str = Field(..., description="产品 ASIN（10 位字母数字）", min_length=10, max_length=10)
    keywords: List[str] = Field(..., description="关键词列表", min_items=1, max_items=100)
    maxPages: int = Field(default=5, description="最大翻页数", ge=1, le=50)
    site: str = Field(default="amazon.com", description="亚马逊站点")
    maxConcurrent: int = Field(default=3, description="最大并发数", ge=1, le=10)
    organicOnly: bool = Field(default=False, description="仅爬取自然结果（跳过广告）")
    maxRetries: int = Field(default=2, description="最大重试次数", ge=0, le=5)
    
    @field_validator('asin')
    @classmethod
    def validate_asin(cls, v: str) -> str:
        """验证 ASIN 格式"""
        if not v.isalnum():
            raise ValueError('ASIN 必须为字母数字')
        if len(v) != 10:
            raise ValueError('ASIN 必须为 10 位')
        return v.upper()
    
    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        """验证关键词"""
        if not v:
            raise ValueError('请至少输入一个关键词')
        for kw in v:
            if not kw or len(kw) > 200:
                raise ValueError('关键词长度必须在 1-200 字符之间')
        return v
    
    @field_validator('site')
    @classmethod
    def validate_site(cls, v: str) -> str:
        """验证站点"""
        allowed_sites = [
            "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
            "amazon.co.jp", "amazon.ca", "amazon.com.au"
        ]
        if v not in allowed_sites:
            raise ValueError(f'不支持的站点：{v}')
        return v


# ========== 响应模型 ==========

class TaskResponse(BaseModel):
    """任务响应"""
    taskId: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    createdAt: datetime = Field(..., description="任务创建时间")
    totalKeywords: Optional[int] = Field(None, description="关键词总数")
    maxPages: Optional[int] = Field(None, description="最大翻页数")
    
    class Config:
        from_attributes = True


class TaskDetail(BaseModel):
    """任务详情"""
    taskId: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    createdAt: datetime = Field(..., description="创建时间")
    updatedAt: datetime = Field(..., description="最后更新时间")
    asin: str = Field(..., description="产品 ASIN")
    site: str = Field(..., description="亚马逊站点")
    maxPages: int = Field(..., description="最大翻页数")
    totalKeywords: int = Field(..., description="关键词总数")
    processedKeywords: int = Field(..., description="已处理的关键词数")
    progress: int = Field(..., description="进度百分比（0-100）")
    errorMessage: Optional[str] = Field(None, description="错误信息")
    
    # 重试相关
    retryCount: int = Field(default=0, description="当前重试次数")
    maxRetries: int = Field(default=2, description="最大重试次数")
    failReason: Optional[str] = Field(None, description="失败原因")
    nextRetryAt: Optional[datetime] = Field(None, description="下次重试时间")
    canRetry: bool = Field(default=False, description="是否可以手动重试")
    
    # 爬虫配置
    maxConcurrent: int = Field(default=3, description="最大并发数")
    organicOnly: bool = Field(default=False, description="仅爬取自然结果")
    
    class Config:
        from_attributes = True


class TaskListItem(BaseModel):
    """任务列表项"""
    taskId: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    createdAt: datetime = Field(..., description="创建时间")
    completedAt: Optional[datetime] = Field(None, description="完成时间")
    totalKeywords: int = Field(..., description="关键词总数")
    processedKeywords: int = Field(..., description="已处理关键词数")
    retryCount: int = Field(default=0, description="重试次数")
    canRetry: bool = Field(default=False, description="是否可以重试")
    
    class Config:
        from_attributes = True


class Pagination(BaseModel):
    """分页信息"""
    page: int = Field(..., description="当前页码")
    pageSize: int = Field(..., description="每页数量")
    total: int = Field(..., description="总记录数")
    totalPages: int = Field(..., description="总页数")


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskListItem] = Field(..., description="任务列表")
    pagination: Pagination = Field(..., description="分页信息")


class RankingResult(BaseModel):
    """排名结果"""
    keyword: str = Field(..., description="关键词")
    organicPage: Optional[int] = Field(None, description="自然排名页码")
    organicPosition: Optional[int] = Field(None, description="自然排名页内位置")
    adPage: Optional[int] = Field(None, description="广告排名页码")
    adPosition: Optional[int] = Field(None, description="广告排名页内位置")
    status: RankingStatus = Field(..., description="结果状态")
    timestamp: datetime = Field(..., description="爬取时间")


class TaskResultsResponse(BaseModel):
    """任务结果响应"""
    taskId: str = Field(..., description="任务 ID")
    asin: str = Field(..., description="产品 ASIN")
    site: str = Field(..., description="亚马逊站点")
    completedAt: Optional[datetime] = Field(None, description="完成时间")
    results: List[RankingResult] = Field(..., description="结果列表")


# ========== 健康检查 ==========

class HealthCheckStatus(str, Enum):
    """健康检查状态"""
    OK = "ok"
    ERROR = "error"


class HealthChecks(BaseModel):
    """健康检查详情"""
    database: HealthCheckStatus = Field(..., description="数据库状态")
    crawler: HealthCheckStatus = Field(..., description="爬虫状态")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="总体健康状态")
    version: str = Field(..., description="应用版本")
    timestamp: datetime = Field(..., description="检查时间")
    checks: HealthChecks = Field(..., description="检查详情")


# ========== 错误响应 ==========

class Error(BaseModel):
    """错误响应"""
    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")
    details: Optional[dict] = Field(None, description="详细错误信息")
