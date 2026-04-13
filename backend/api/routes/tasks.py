"""
任务 API 路由
提供任务管理相关的 RESTful 接口
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from backend.models.schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskDetail,
    TaskListResponse,
    TaskResultsResponse,
    Error,
    TaskStatus,
)
from backend.services.task_service import get_task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=201,
    responses={
        400: {"model": Error, "description": "请求参数错误"},
        429: {"model": Error, "description": "请求频率超限"},
    }
)
async def create_task(request: TaskCreateRequest):
    """
    提交排名追踪任务
    
    - **asin**: 产品 ASIN（10 位字母数字）
    - **keywords**: 关键词列表（1-100 个）
    - **maxPages**: 最大翻页数（1-50，默认 5）
    - **site**: 亚马逊站点（默认 amazon.com）
    """
    try:
        task_service = get_task_service()
        task_id = await task_service.create_task(request)
        
        # 获取任务信息
        task_detail = await task_service.get_task_detail(task_id)
        
        return TaskResponse(
            taskId=task_id,
            status=TaskStatus(task_detail['status']),
            createdAt=task_detail['createdAt'],
            totalKeywords=task_detail['totalKeywords'],
            maxPages=task_detail['maxPages'],
        )
    
    except ValueError as e:
        logger.warning(f"创建任务参数错误：{e}")
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_PARAMS",
            "message": str(e),
        })
    
    except Exception as e:
        logger.error(f"创建任务失败：{e}")
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })


@router.get(
    "",
    response_model=TaskListResponse,
    responses={
        200: {"description": "成功返回任务列表"},
    }
)
async def list_tasks(
    status: Optional[str] = Query(None, description="按任务状态筛选"),
    asin: Optional[str] = Query(None, description="按 ASIN 筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取任务列表
    
    支持分页、状态筛选和 ASIN 搜索
    """
    try:
        task_service = get_task_service()
        result = await task_service.get_task_list_paginated(
            status=status,
            asin=asin,  # 传入 asin 参数
            page=page,
            page_size=page_size
        )
        
        return TaskListResponse(
            tasks=result['tasks'],
            pagination=result['pagination']
        )
    
    except Exception as e:
        logger.error(f"获取任务列表失败：{e}")
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })


@router.get(
    "/{task_id}",
    response_model=TaskDetail,
    responses={
        404: {"model": Error, "description": "任务不存在"},
    }
)
async def get_task(task_id: str):
    """
    查询任务状态
    
    获取指定任务的详细状态信息
    """
    try:
        task_service = get_task_service()
        task = await task_service.get_task_detail(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail={
                "code": "TASK_NOT_FOUND",
                "message": "指定的任务不存在",
                "details": {"taskId": task_id}
            })
        
        return TaskDetail(**task)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"获取任务详情失败：{task_id}, 错误：{e}")
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })


@router.delete(
    "/{task_id}",
    response_model=TaskResponse,
    responses={
        400: {"model": Error, "description": "任务无法取消"},
        404: {"model": Error, "description": "任务不存在"},
    }
)
async def cancel_task(task_id: str):
    """
    取消任务
    
    仅支持取消状态为 pending 或 running 的任务
    """
    try:
        task_service = get_task_service()
        
        # 检查任务是否存在
        task = await task_service.get_task_detail(task_id)
        if not task:
            raise HTTPException(status_code=404, detail={
                "code": "TASK_NOT_FOUND",
                "message": "指定的任务不存在",
                "details": {"taskId": task_id}
            })
        
        # 尝试取消
        success = await task_service.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail={
                "code": "CANNOT_CANCEL",
                "message": "任务已完成或已失败，无法取消",
                "details": {
                    "taskId": task_id,
                    "currentStatus": task['status']
                }
            })
        
        # 返回更新后的任务信息
        updated_task = await task_service.get_task_detail(task_id)
        
        return TaskResponse(
            taskId=task_id,
            status=TaskStatus(updated_task['status']),
            createdAt=updated_task['createdAt'],
            totalKeywords=updated_task['totalKeywords'],
            maxPages=updated_task['maxPages'],
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"取消任务失败：{task_id}, 错误：{e}")
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })


@router.get(
    "/{task_id}/results",
    response_model=TaskResultsResponse,
    responses={
        400: {"model": Error, "description": "任务尚未完成"},
        404: {"model": Error, "description": "任务不存在"},
    }
)
async def get_task_results(task_id: str):
    """
    获取任务结果
    
    获取指定任务的排名结果数据
    """
    try:
        task_service = get_task_service()
        
        # 获取任务信息
        task = await task_service.get_task_detail(task_id)
        if not task:
            raise HTTPException(status_code=404, detail={
                "code": "TASK_NOT_FOUND",
                "message": "指定的任务不存在",
                "details": {"taskId": task_id}
            })
        
        # 获取结果
        result = await task_service.get_task_results(task_id)
        
        if not result:
            raise HTTPException(status_code=404, detail={
                "code": "TASK_NOT_FOUND",
                "message": "指定的任务不存在",
            })
        
        return TaskResultsResponse(**result)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"获取任务结果失败：{task_id}, 错误：{e}")
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })


@router.post(
    "/{task_id}/retry",
    response_model=TaskResponse,
    status_code=201,
    responses={
        400: {"model": Error, "description": "任务不允许重试"},
        404: {"model": Error, "description": "任务不存在"},
    }
)
async def retry_task(task_id: str):
    """手动重试任务（创建新任务）"""
    try:
        task_service = get_task_service()
        new_task_id = await task_service.retry_task(task_id)
        new_task = await task_service.get_task_detail(new_task_id)
        
        return TaskResponse(
            taskId=new_task_id,
            status=TaskStatus(new_task['status']),
            createdAt=new_task['createdAt'],
            totalKeywords=new_task['totalKeywords'],
            maxPages=new_task['maxPages'],
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_PARAMS",
            "message": str(e),
        })
    except Exception as e:
        logger.error(f"重试任务失败：{task_id}, 错误：{e}")
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })


@router.post(
    "/{task_id}/abandon",
    response_model=TaskResponse,
    responses={
        400: {"model": Error, "description": "任务无法放弃"},
        404: {"model": Error, "description": "任务不存在"},
    }
)
async def abandon_task(task_id: str):
    """放弃任务（取消 retrying 状态的任务）"""
    try:
        task_service = get_task_service()
        task = await task_service.get_task_detail(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail={
                "code": "TASK_NOT_FOUND",
                "message": "指定的任务不存在",
            })
        
        if task['status'] not in ['retrying', 'running', 'pending']:
            raise HTTPException(status_code=400, detail={
                "code": "CANNOT_ABANDON",
                "message": "任务已完成或已失败，无法放弃",
            })
        
        success = await task_service.cancel_task(task_id)
        if not success:
            raise HTTPException(status_code=400, detail={
                "code": "CANNOT_ABANDON",
                "message": "任务无法放弃",
            })
        
        updated_task = await task_service.get_task_detail(task_id)
        return TaskResponse(
            taskId=task_id,
            status=TaskStatus(updated_task['status']),
            createdAt=updated_task['createdAt'],
            totalKeywords=updated_task['totalKeywords'],
            maxPages=updated_task['maxPages'],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"放弃任务失败：{task_id}, 错误：{e}")
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        })
