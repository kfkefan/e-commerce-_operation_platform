"""
SQLAlchemy 表模型
定义数据库表结构
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Task(Base):
    """任务主表"""
    __tablename__ = 'tasks'
    
    id = Column(String(36), primary_key=True, comment='任务 ID (UUID)')
    asin = Column(String(10), nullable=False, comment='产品 ASIN')
    site = Column(String(50), nullable=False, default='amazon.com', comment='亚马逊站点')
    max_pages = Column(Integer, nullable=False, default=5, comment='最大翻页数 (1-50)')
    status = Column(String(20), nullable=False, default='pending', comment='任务状态')
    total_keywords = Column(Integer, nullable=False, comment='关键词总数')
    processed_keywords = Column(Integer, nullable=False, default=0, comment='已处理关键词数')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        comment='更新时间'
    )
    completed_at = Column(DateTime, nullable=True, comment='完成时间')
    error_message = Column(Text, nullable=True, comment='错误信息')
    
    # 关系
    keywords = relationship("TaskKeyword", back_populates="task", cascade="all, delete-orphan")
    results = relationship("TaskResult", back_populates="task", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_created_at', 'created_at', mysql_length=19),
        Index('idx_tasks_status_created', 'status', 'created_at', mysql_length=19),
        Index('idx_tasks_asin', 'asin'),
    )


class TaskKeyword(Base):
    """任务关键词表"""
    __tablename__ = 'task_keywords'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增 ID')
    task_id = Column(String(36), ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, comment='关联任务 ID')
    keyword = Column(String(200), nullable=False, comment='关键词文本')
    priority = Column(Integer, nullable=False, default=0, comment='处理优先级')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    
    # 关系
    task = relationship("Task", back_populates="keywords")
    
    # 索引
    __table_args__ = (
        Index('idx_task_keywords_task_id', 'task_id'),
        Index('idx_task_keywords_task_priority', 'task_id', 'priority'),
    )


class TaskResult(Base):
    """任务结果表"""
    __tablename__ = 'task_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增 ID')
    task_id = Column(String(36), ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, comment='关联任务 ID')
    keyword = Column(String(200), nullable=False, comment='关键词文本')
    organic_page = Column(Integer, nullable=True, comment='自然排名页码')
    organic_position = Column(Integer, nullable=True, comment='自然排名页内位置')
    ad_page = Column(Integer, nullable=True, comment='广告排名页码')
    ad_position = Column(Integer, nullable=True, comment='广告排名页内位置')
    status = Column(String(30), nullable=False, comment='结果状态')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='爬取时间')
    
    # 关系
    task = relationship("Task", back_populates="results")
    
    # 索引
    __table_args__ = (
        Index('idx_task_results_task_id', 'task_id'),
        Index('idx_task_results_task_keyword', 'task_id', 'keyword'),
        Index('idx_task_results_task_status', 'task_id', 'status'),
    )


class Config(Base):
    """系统配置表"""
    __tablename__ = 'config'
    
    key = Column(String(100), primary_key=True, comment='配置键')
    value = Column(Text, nullable=False, comment='配置值 (JSON 格式)')
    description = Column(String(500), nullable=True, comment='配置描述')
    updated_at = Column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        comment='更新时间'
    )
