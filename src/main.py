#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cyber-Lab-Agents - 主入口
子阶段5：外部接口（FastAPI + 飞书Webhook + 看板）
"""

import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
import uvicorn

# 导入核心模块
from agent_base import AgentRole, AgentRegistry
from workflow import WorkflowEngine, TaskStatus, IntentClassifier, route_task
from memory_skills import LocalMemoryBank, SkillRegistry, RAGContextBuilder


# ====================
# FastAPI setup
# ====================

app = FastAPI(
    title="Cyber-Lab-Agents API",
    description="赛博课题组 - 多智能体科研协作系统",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================
# 全局状态
# ====================

engine = WorkflowEngine()
memory_bank = LocalMemoryBank("./memory_bank")
skill_registry = SkillRegistry()
registry = AgentRegistry()


# ====================
# 数据模型
# ====================

class MessageRequest(BaseModel):
    """消息请求"""
    sender_id: str
    content: str


class TaskCreateRequest(BaseModel):
    """任务创建请求"""
    title: str
    description: str
    intent_type: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    """任务更新请求"""
    task_id: str
    action: str  # approve, reject, submit
    feedback: Optional[str] = None


# ====================
# API 路由
# ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Cyber-Lab-Agents",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/agents")
async def list_agents():
    """列出所有 Agent"""
    agents = registry.list_all()
    return {
        "agents": [
            {
                "role": a.role.value,
                "name": a.name,
                "description": a.description
            }
            for a in agents
        ]
    }


@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None):
    """列出任务"""
    task_status = TaskStatus(status) if status else None
    tasks = engine.list_tasks(task_status)
    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value,
                "intent_type": t.intent_type.value,
                "retry_count": t.retry_count,
                "created_at": t.created_at.isoformat()
            }
            for t in tasks
        ]
    }


@app.post("/api/tasks")
async def create_task(req: TaskCreateRequest):
    """创建任务"""
    # 路由到合适的 Agent
    task = engine.create_task(
        title=req.title,
        description=req.description,
        creator=AgentRole.MENTOR
    )
    
    assignee = route_task(task, engine)
    engine.assign_task(task.id, assignee)
    
    return {
        "task_id": task.id,
        "title": task.title,
        "assignee": assignee.value,
        "intent_type": task.intent_type.value
    }


@app.post("/api/tasks/update")
async def update_task(req: TaskUpdateRequest):
    """更新任务状态"""
    task = engine.get_task(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if req.action == "approve":
        engine.approve_task(task.id)
    elif req.action == "reject":
        if not req.feedback:
            raise HTTPException(status_code=400, detail="Feedback required for rejection")
        engine.reject_task(task.id, req.feedback)
        
        # 检查是否触发PUA，并异步发送给对应小导
        pua = engine.trigger_pua(task.id)
        if pua:
            # 异步发送PUA消息（小导收到提醒）
            import asyncio
            asyncio.create_task(asyncio.to_thread(engine.send_pua_to_pi, task.id))
            return {"status": "rejected", "pua": pua, "pua_sent": True}
    elif req.action == "submit":
        engine.submit_for_review(task.id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    return {"status": "ok", "task_status": task.status.value}


@app.get("/api/memory")
async def search_memory(q: str, limit: int = 3):
    """搜索记忆"""
    results = memory_bank.search(q, limit=limit)
    return {
        "results": [
            {
                "id": r.id,
                "topic": r.topic,
                "content": r.content[:200],
                "created_at": r.created_at.isoformat()
            }
            for r in results
        ]
    }


@app.get("/api/skills")
async def list_skills():
    """列出技能"""
    skills = skill_registry.list_enabled()
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "required_params": s.required_params
            }
            for s in skills
        ]
    }


# ====================
# 飞书 Webhook 接收
# ====================

class FeishuWebhook:
    """飞书消息接收与处理"""
    
    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID", "")
        self.app_secret = os.getenv("FEISHU_APP_SECRET", "")
        self.verify_token = os.getenv("FEISHU_VERIFY_TOKEN", "")
    
    async def handle_message(self, message: dict) -> str:
        """处理飞书消息"""
        # 提取消息内容
        event = message.get("event", {})
        msg_type = event.get("msg_type", "text")
        content = event.get("content", {})
        sender_id = event.get("sender_id", {}).get("open_id", "")
        text = content.get("text", "") if msg_type == "text" else str(content)
        
        # 意图识别
        intent = IntentClassifier.classify(text)
        
        # 路由处理
        if intent.value == "casual":
            # 闲聊 -> 马屁精
            return "收到！有什么想聊的吗？我陪你聊聊～"
        else:
            # 创建任务
            task = engine.create_task(
                title=text[:50],
                description=text,
                creator=AgentRole.MENTOR
            )
            assignee = route_task(task, engine)
            engine.assign_task(task.id, assignee)
            
            return f"好的，已创建任务 [{task.title}]，分配给 {assignee.value} 处理。"
    
    def verify(self, request: Request) -> bool:
        """验证飞书请求"""
        # 简化验证：检查 verify_token
        token = request.query_params.get("verify_token", "")
        return token == self.verify_token if self.verify_token else True


feishu_webhook = FeishuWebhook()


@app.post("/webhook/feishu")
async def feishu_message(request: Request):
    """飞书消息回调"""
    try:
        body = await request.json()
        
        # 验证
        if not feishu_webhook.verify(request):
            return {"code": 401, "msg": "verify failed"}
        
        # 处理消息类型
        event_type = body.get("event", {}).get("type", "")
        
        if event_type == "url_verification":
            # URL 验证
            return {
                "challenge": body.get("event", {}).get("challenge", "")
            }
        elif event_type == "message":
            # 处理消息
            response = await feishu_webhook.handle_message(body)
            return {"code": 0, "msg": "success", "data": {"text": response}}
        
        return {"code": 0, "msg": "success"}
    
    except Exception as e:
        return {"code": 500, "msg": str(e)}


# ====================
# 状态看板（HTML）
# ====================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cyber-Lab-Agents 看板</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
        .status-item { text-align: center; padding: 15px; border-radius: 8px; }
        .status-pending { background: #fee; color: #c00; }
        .status-in_progress { background: #efe; color: #060; }
        .status-review { background: #eef; color: #006; }
        .status-completed { background: #eee; color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f9f9f9; }
        .btn { background: #667eea; color: white; border: none; padding: 10px 20px; 
              border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #5568d3; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏢 Cyber-Lab-Agents 看板</h1>
        <p>赛博课题组 - 多智能体科研协作系统</p>
    </div>
    
    <div class="card">
        <h2>📊 任务概览</h2>
        <div class="status-grid">
            <div class="status-item status-pending">
                <h3>{{pending}}</h3>
                <p>待处理</p>
            </div>
            <div class="status-item status-in_progress">
                <h3>{{in_progress}}</h3>
                <p>进行中</p>
            </div>
            <div class="status-item status-review">
                <h3>{{review}}</h3>
                <p>待审核</p>
            </div>
            <div class="status-item status-completed">
                <h3>{{completed}}</h3>
                <p>已完成</p>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>📋 任务列表</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>标题</th>
                    <th>状态</th>
                    <th>类型</th>
                    <th>重试</th>
                    <th>创建时间</th>
                </tr>
            </thead>
            <tbody>
                {{tasks}}
            </tbody>
        </table>
    </div>
    
    <div class="card">
        <h2>🤖 Agent 状态</h2>
        <table>
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>角色</th>
                    <th>描述</th>
                </tr>
            </thead>
            <tbody>
                {{agents}}
            </tbody>
        </table>
    </div>
</body>
</html>
"""


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """状态看板"""
    # 统计
    tasks = engine.list_tasks()
    pending = len([t for t in tasks if t.status == TaskStatus.PENDING])
    in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
    review = len([t for t in tasks if t.status == TaskStatus.REVIEW])
    completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
    
    # 任务表格
    task_rows = []
    for t in tasks[:20]:
        task_rows.append(f"<tr><td>{t.id}</td><td>{t.title}</td><td>{t.status.value}</td>"
                     f"<td>{t.intent_type.value}</td><td>{t.retry_count}/{t.max_retries}</td>"
                     f"<td>{t.created_at.strftime('%m-%d %H:%M')}</td></tr>")
    
    # Agent表格
    agent_rows = []
    for a in registry.list_all():
        agent_rows.append(f"<tr><td>{a.name}</td><td>{a.role.value}</td><td>{a.description}</td></tr>")
    
    html = DASHBOARD_HTML.replace("{{pending}}", str(pending))
    html = html.replace("{{in_progress}}", str(in_progress))
    html = html.replace("{{review}}", str(review))
    html = html.replace("{{completed}}", str(completed))
    html = html.replace("{{tasks}}", "".join(task_rows))
    html = html.replace("{{agents}}", "".join(agent_rows))
    
    return html


# ====================
# 主入口
# ====================

def main():
    """启动服务"""
    port = int(os.getenv("DASHBOARD_PORT", "8000"))
    print(f"🚀 Cyber-Lab-Agents 启动中...")
    print(f"📊 看板: http://localhost:{port}/dashboard")
    print(f"📖 API docs: http://localhost:{port}/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()