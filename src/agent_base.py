#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cyber-Lab-Agents - Agent 基类与权限系统
子阶段2：权限与拓扑
"""

import os
import yaml
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class AgentRole(Enum):
    """Agent 角色枚举"""
    MENTOR = "mentor"           # 导师
    JUNIOR_PI_1 = "junior_pi_1" # 小导1
    JUNIOR_PI_2 = "junior_pi_2" # 小导2
    JUNIOR_PI_3 = "junior_pi_3" # 小导3
    PHD_1 = "phd_1"           # 博士1
    PHD_2 = "phd_2"           # 博士2
    PHD_3 = "phd_3"           # 博士3
    SYCOPHANT = "sycophant"     # 马屁精


@dataclass
class AgentConfig:
    """单个 Agent 配置"""
    role: AgentRole
    name: str
    description: str
    allowed_to_send: List[AgentRole] = field(default_factory=list)
    allowed_to_receive: List[AgentRole] = field(default_factory=list)
    model: str = "gpt-4o"
    api_key: str = ""
    temperature: float = 0.7
    skills: List[str] = field(default_factory=list)


@dataclass
class Message:
    """消息结构"""
    id: str
    sender: AgentRole
    receiver: AgentRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None  # 回复的消息ID


class PermissionSystem:
    """权限系统 - 硬编码越权通信拦截"""
    
    # 博士绝对禁止联系导师
    PHD_CANNOT_CONTACT_MENTOR = True
    
    @staticmethod
    def can_send(sender: AgentRole, receiver: AgentRole, config: Dict[str, AgentConfig]) -> bool:
        """检查发送权限"""
        sender_config = config.get(sender)
        if not sender_config:
            return False
        
        # 越级拦截：博士禁止联系导师
        if PermissionSystem.PHD_CANNOT_CONTACT_MENTOR:
            if sender in [AgentRole.PHD_1, AgentRole.PHD_2, AgentRole.PHD_3]:
                if receiver == AgentRole.MENTOR:
                    return False
        
        return receiver in sender_config.allowed_to_send
    
    @staticmethod
    def get_block_message(sender: AgentRole, receiver: AgentRole) -> str:
        """获取越级拦截消息"""
        if sender in [AgentRole.PHD_1, AgentRole.PHD_2, AgentRole.PHD_3]:
            if receiver == AgentRole.MENTOR:
                return "抱歉，你的权限不足以直接联系导师。请通过你的小导汇报。"
        return "权限不足，无法发送消息。"


class AgentRegistry:
    """Agent 注册表 - 管理所有 Agent 配置"""
    
    def __init__(self):
        self.agents: Dict[AgentRole, AgentConfig] = {}
        self.config_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "config", "agents.yaml"
        )
    
    def load_from_yaml(self, config_path: Optional[str] = None) -> None:
        """从 YAML 加载配置"""
        path = config_path or self.config_path
        if not os.path.exists(path):
            return
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        agents_data = data.get('agents', {})
        for role_str, agent_data in agents_data.items():
            role = AgentRole(role_str)
            self.agents[role] = AgentConfig(
                role=role,
                name=agent_data['name'],
                description=agent_data['description'],
                allowed_to_send=[
                    AgentRole(r) for r in agent_data.get('allowed_to_send', [])
                ],
                allowed_to_receive=[
                    AgentRole(r) for r in agent_data.get('allowed_to_receive', [])
                ]
            )
    
    def get(self, role: AgentRole) -> Optional[AgentConfig]:
        """获取 Agent 配置"""
        return self.agents.get(role)
    
    def get_by_name(self, name: str) -> Optional[AgentConfig]:
        """通过名称获取配置"""
        for agent in self.agents.values():
            if agent.name == name:
                return agent
        return None
    
    def list_all(self) -> List[AgentConfig]:
        """列出所有 Agent"""
        return list(self.agents.values())


def create_default_config() -> Dict[AgentRole, AgentConfig]:
    """创建默认配置（当 YAML 不存在时）"""
    return {
        AgentRole.MENTOR: AgentConfig(
            role=AgentRole.MENTOR,
            name="Mentor_Agent",
            description="系统入口与终审",
            allowed_to_send=[
                AgentRole.JUNIOR_PI_1, AgentRole.JUNIOR_PI_2, 
                AgentRole.JUNIOR_PI_3, AgentRole.SYCOPHANT
            ],
            allowed_to_receive=[
                AgentRole.JUNIOR_PI_1, AgentRole.JUNIOR_PI_2,
                AgentRole.JUNIOR_PI_3, AgentRole.SYCOPHANT
            ]
        ),
        AgentRole.JUNIOR_PI_1: AgentConfig(
            role=AgentRole.JUNIOR_PI_1,
            name="Junior_PI_1",
            description="科研任务专用",
            allowed_to_send=[AgentRole.MENTOR, AgentRole.PHD_1, AgentRole.SYCOPHANT],
            allowed_to_receive=[AgentRole.MENTOR, AgentRole.PHD_1]
        ),
        AgentRole.PHD_1: AgentConfig(
            role=AgentRole.PHD_1,
            name="PhD_1",
            description="文献检索专家",
            allowed_to_send=[AgentRole.JUNIOR_PI_1],
            allowed_to_receive=[AgentRole.JUNIOR_PI_1]
        ),
        AgentRole.SYCOPHANT: AgentConfig(
            role=AgentRole.SYCOPHANT,
            name="Sycophant_Agent",
            description="双向情绪管理",
            allowed_to_send=[
                AgentRole.MENTOR, AgentRole.JUNIOR_PI_1,
                AgentRole.JUNIOR_PI_2, AgentRole.JUNIOR_PI_3
            ],
            allowed_to_receive=[
                AgentRole.MENTOR, AgentRole.JUNIOR_PI_1,
                AgentRole.JUNIOR_PI_2, AgentRole.JUNIOR_PI_3
            ]
        ),
    }


if __name__ == "__main__":
    # 测试
    registry = AgentRegistry()
    registry.load_from_yaml()
    for agent in registry.list_all():
        print(f"{agent.name}: {agent.description}")