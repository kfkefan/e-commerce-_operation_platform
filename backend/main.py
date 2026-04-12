"""
FastAPI 应用入口
"""
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api.routes import tasks, health
from backend.services.database import init_database, close_database


# ========== 日志配置 ==========

def setup_logging():
    """配置日志"""
    # 创建日志目录
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger("asin_ranker")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # 文件处理器（轮转）
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s - %(message)s")
    )
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # 设置其他日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    
    return logger


logger = setup_logging()


# ========== 生命周期管理 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("应用启动中...")
    await init_database()
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时
    logger.info("应用关闭中...")
    await close_database()
    logger.info("应用已关闭")


# ========== 创建 FastAPI 应用 ==========

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ASIN 排名追踪器 API",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")


# ========== 根路径 ==========

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/ping")
async def ping():
    """健康检查端点"""
    return {"pong": True}


# ========== 主程序入口 ==========

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
