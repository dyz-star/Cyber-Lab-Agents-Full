#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cyber-Lab-Agents - 工作流引擎
子阶段3：工作流引擎（路由 + 竞标 + max_retries打回）
"""

import os
import yaml
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio

# 导入权限系统
from agent_base import AgentRole, Message, PermissionSystem, AgentRegistry


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"           # 待处理
    IN_PROGRESS = "in_progress"    # 进行中
    REVIEW = "review"            # 待审核
    REVISION = "revision"         # 打回重做
    COMPLETED = "completed"      # 完成
    FAILED = "failed"           # 失败


class IntentType(Enum):
    """意图类型"""
    CASUAL = "casual"           # 闲聊
    RESEARCH = "research"        # 科研任务
    CODING = "coding"           # 代码任务
    WRITING = "writing"         # 写作任务
    SYSTEM = "system"           # 系统命令


@dataclass
class Task:
    """任务结构"""
    id: str
    title: str
    description: str
    intent_type: IntentType
    creator: AgentRole
    assignee: Optional[AgentRole] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentClassifier:
    """意图识别 - 简单关键词匹配"""
    
    KEYWORDS = {
        IntentType.CASUAL: ["闲聊", "聊天", "吃饭", "最近怎样", "天气", "你好"],
        IntentType.RESEARCH: ["调研", "文献", "研究", "搜索", "分析", "论文"],
        IntentType.CODING: ["代码", "编程", "写程序", "python", "脚本"],
        IntentType.WRITING: ["写作", "写文章", "编辑", "科普", "公众号"],
    }
    
    @classmethod
    def classify(cls, text: str) -> IntentType:
        """识别意图"""
        text_lower = text.lower()
        for intent, keywords in cls.KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return intent
        return IntentType.SYSTEM


class WorkflowEngine:
    """工作流引擎"""
    
    MAX_RETRIES = 3           # 最大重试次数（硬编码防死循环）
    RETRY_DELAY = 60          # 重试间隔（秒）
    COMPLEX_THRESHOLD = 500  # 复杂任务阈值
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.registry.load_from_yaml()
        self.tasks: Dict[str, Task] = {}
        self.messages: List[Message] = []
        self.pua_enabled = True
        
    def create_task(self, title: str, description: str, 
                   creator: AgentRole) -> Task:
        """创建任务"""
        intent_type = IntentClassifier.classify(description)
        
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            intent_type=intent_type,
            creator=creator,
            max_retries=self.MAX_RETRIES
        )
        self.tasks[task.id] = task
        return task
    
    def assign_task(self, task_id: str, assignee: AgentRole) -> bool:
        """分配任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # 检查权限
        if not PermissionSystem.can_send(task.creator, assignee, self.registry.agents):
            return False
        
        task.assignee = assignee
        task.status = TaskStatus.IN_PROGRESS
        return True
    
    def submit_for_review(self, task_id: str) -> bool:
        """提交审核"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.REVIEW
        task.updated_at = datetime.now()
        return True
    
    def approve_task(self, task_id: str) -> bool:
        """审核通过"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        return True
    
    def reject_task(self, task_id: str, feedback: str) -> bool:
        """打回重做（带 max_retries 硬编码）"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # 硬编码：检查重试次数，防止死循环
        if task.retry_count >= task.max_retries:
            task.status = TaskStatus.FAILED
            return False
        
        task.retry_count += 1
        task.status = TaskStatus.REVISION
        task.updated_at = datetime.now()
        
        # 在 metadata 中记录反馈
        task.metadata['rejection_feedback'] = feedback
        
        return True
    
    def trigger_pua(self, task_id: str) -> Optional[str]:
        """触发 PUA 机制 - 返回消息但不自动发送（供外部调用）"""
        if not self.pua_enabled:
            return None
        
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        # 触发条件：打回超过2次
        if task.retry_count >= 2:
            pua_messages = [
                "小导啊，这个任务怎么搞的？导师已经打回一次了，再这样下去课题组要被笑话了。",
                "进度太慢了，其他组都在赶进度，我们不能掉队啊。",
                "这个产出有点水啊，要不要我再带带你？"
            ]
            return pua_messages[task.retry_count - 2 % len(pua_messages)]
        
        return None
    
    def send_pua_to_pi(self, task_id: str) -> bool:
        """发送 PUA 消息给小导（异步执行）"""
        task = self.tasks.get(task_id)
        if not task or not task.assignee:
            return False
        
        pua_msg = self.trigger_pua(task_id)
        if not pua_msg:
            return False
        
        # 构建消息
        message = Message(
            id=str(uuid.uuid4())[:8],
            sender=AgentRole.SYCOPHANT,
            receiver=task.assignee,
            content=f"[PUA通知] 任务 {task.title} 已打回 {task.retry_count} 次\n\n{pua_msg}",
            metadata={"task_id": task_id, "type": "pua"}
        )
        self.messages.append(message)
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """列出任务"""
        if status:
            return [t for t in self.tasks.values() if t.status == status]
        return list(self.tasks.values())


class BiddingSystem:
    """竞标系统 - 复杂任务触发"""
    
    def __init__(self):
        self.bids: Dict[str, Dict[AgentRole, str]] = {}  # task_id -> {pi -> proposal}
    
    def open_bidding(self, task_id: str, pi_list: List[AgentRole]) -> None:
        """开启竞标"""
        self.bids[task_id] = {}
    
    def submit_bid(self, task_id: str, pi: AgentRole, proposal: str) -> bool:
        """提交标书"""
        if task_id not in self.bids:
            return False
        self.bids[task_id][pi] = proposal
        return True
    
    def get_winner(self, task_id: str) -> Optional[AgentRole]:
        """获取中标者"""
        if task_id not in self.bids:
            return None
        bids = self.bids[task_id]
        if not bids:
            return None
        # 简单策略：返回第一个（可扩展为评分制）
        return list(bids.keys())[0]


def route_task(task: Task, engine: WorkflowEngine) -> AgentRole:
    """路由任务到合适的 Agent"""
    
    # 闲聊 -> 马屁精
    if task.intent_type == IntentType.CASUAL:
        return AgentRole.SYCOPHANT
    
    # 科研任务 -> 小导1
    if task.intent_type == IntentType.RESEARCH:
        # 复杂任务触发竞标
        if len(task.description) > engine.COMPLEX_THRESHOLD:
            return AgentRole.JUNIOR_PI_1  # 后续触发竞标
        return AgentRole.JUNIOR_PI_1
    
    # 代码任务 -> 小导2
    if task.intent_type == IntentType.CODING:
        return AgentRole.JUNIOR_PI_2
    
    # 写作任务 -> 小导3
    if task.intent_type == IntentType.WRITING:
        return AgentRole.JUNIOR_PI_3
    
    # 默认 -> 小导1
    return AgentRole.JUNIOR_PI_1


if __name__ == "__main__":
    # 测试
    engine = WorkflowEngine()
    
    # 创建任务
    task = engine.create_task(
        title="测试任务",
        description="调研PET化学回收的最新进展",
        creator=AgentRole.MENTOR
    )
    print(f"创建任务: {task.id} - {task.title}")
    print(f"意图类型: {task.intent_type}")
    
    # 路由
    assignee = route_task(task, engine)
    print(f"分配给: {assignee}")
    
    # 模拟打回
    engine.reject_task(task.id, "内容不够深入")
    print(f"打回次数: {task.retry_count}")
    
    # 触发PUA
    engine.reject_task(task.id, "还是不够")
    pua_msg = engine.trigger_pua(task.id)
    if pua_msg:
        print(f"PUA消息: {pua_msg}")