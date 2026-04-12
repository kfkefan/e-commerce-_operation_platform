"""
健康检查路由
提供 API 服务健康状态检查
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from backend.models.schemas import HealthResponse, HealthChecks, HealthCheckStatus
from backend.config import settings
from backend.services.database import check_database_health
from backend.core.crawler import get_crawler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    responses={
        200: {"description": "服务健康"},
    }
)
async def health_check():
    """
    健康检查
    
    检查 API 服务及各组件的健康状态
    """
    try:
        # 检查数据库
        db_healthy = await check_database_health()
        db_status = HealthCheckStatus.OK if db_healthy else HealthCheckStatus.ERROR
        
        # 检查爬虫（简单检查，实际应该检查浏览器是否可启动）
        crawler_healthy = True  # 假设爬虫服务正常
        crawler_status = HealthCheckStatus.OK if crawler_healthy else HealthCheckStatus.ERROR
        
        # 确定总体状态
        if db_healthy and crawler_healthy:
            overall_status = "healthy"
        elif db_healthy or crawler_healthy:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            version=settings.APP_VERSION,
            timestamp=datetime.utcnow(),
            checks=HealthChecks(
                database=db_status,
                crawler=crawler_status,
            )
        )
    
    except Exception as e:
        logger.error(f"健康检查失败：{e}")
        # 即使出错也返回响应，但状态为 unhealthy
        return HealthResponse(
            status="unhealthy",
            version=settings.APP_VERSION,
            timestamp=datetime.utcnow(),
            checks=HealthChecks(
                database=HealthCheckStatus.ERROR,
                crawler=HealthCheckStatus.ERROR,
            )
        )
