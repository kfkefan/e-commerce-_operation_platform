import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List

# WebSocket 路由
websocket_router = APIRouter()

# 活跃的 WebSocket 连接列表
active_connections: List[WebSocket] = []

@websocket_router.websocket("/tasks")
async def websocket_task_status(websocket: WebSocket):
    """
    WebSocket 任务状态推送端点
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # 等待客户端消息（保持连接）
            data = await websocket.receive_text()
            # 可以处理客户端发来的消息（如心跳）
            print(f"收到客户端消息：{data}")
    except WebSocketDisconnect:
        print("客户端断开连接")
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket 错误：{e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def push_to_all_clients(message: dict):
    """
    向所有连接的客户端推送消息
    """
    if not active_connections:
        return
    
    message_str = json.dumps(message)
    
    # 断开失败的连接
    disconnected = []
    
    for connection in active_connections:
        try:
            await connection.send_text(message_str)
        except Exception as e:
            print(f"发送消息失败：{e}")
            disconnected.append(connection)
    
    # 清理断开的连接
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


def push_task_status(task_id: str, status: str, progress_data: dict = None):
    """
    推送任务状态变更消息（同步版本，用于在业务逻辑中调用）
    """
    message = {
        "type": "task_status_update",
        "task_id": task_id,
        "status": status,
        "timestamp": asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0
    }
    
    if progress_data:
        message.update(progress_data)
    
    # 创建异步任务发送消息
    asyncio.create_task(push_to_all_clients(message))
