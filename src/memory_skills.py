#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cyber-Lab-Agents - 记忆与技能系统
子阶段4：本地记忆库 + Skill挂载
"""

import os
import json
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re


@dataclass
class Memory:
    """记忆条目"""
    id: str
    topic: str
    content: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LocalMemoryBank:
    """本地记忆库 - Markdown 文件存储"""
    
    def __init__(self, base_path: str = "./memory_bank"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_date_file(self, date: Optional[datetime] = None) -> Path:
        """获取日期文件名"""
        d = date or datetime.now()
        return self.base_path / f"{d.strftime('%Y-%m-%d')}.md"
    
    def save(self, topic: str, content: str, tags: Optional[List[str]] = None) -> str:
        """保存记忆"""
        mem_id = str(uuid.uuid4())[:8]
        tags = tags or []
        
        # 构建 Markdown
        lines = [
            f"## {mem_id} - {topic}",
            f"**标签**: {', '.join(tags)}",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            content,
            "",
            "---",
            ""
        ]
        
        # 追加到文件
        file_path = self._get_date_file()
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        return mem_id
    
    def search(self, query: str, limit: int = 3) -> List[Memory]:
        """搜索记忆（简单关键词匹配）"""
        results = []
        query_lower = query.lower()
        
        # 遍历所有记忆文件
        for md_file in self.base_path.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单匹配
                if query_lower in content.lower():
                    # 解析记忆条目
                    entries = content.split("## ")
                    for entry in entries[1:]:  # 跳过标题
                        lines = entry.split("\n", 4)
                        if len(lines) >= 3:
                            mem_id = lines[0].split(" - ")[0].strip()
                            topic = lines[0].split(" - ", 1)[1].strip() if " - " in lines[0] else ""
                            mem_content = lines[3] if len(lines) > 3 else ""
                            
                            if query_lower in mem_content.lower():
                                results.append(Memory(
                                    id=mem_id,
                                    topic=topic,
                                    content=mem_content,
                                    tags=[]
                                ))
            except Exception:
                continue
        
        # 按时间倒序
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]
    
    def list_all(self, limit: int = 10) -> List[Memory]:
        """列出最近记忆"""
        memories = []
        for md_file in sorted(self.base_path.glob("*.md"), reverse=True)[:5]:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                entries = content.split("## ")
                for entry in entries[1:]:
                    lines = entry.split("\n", 4)
                    if len(lines) >= 3:
                        mem_id = lines[0].split(" - ")[0].strip()
                        topic = lines[0].split(" - ", 1)[1].strip() if " - " in lines[0] else ""
                        memories.append(Memory(
                            id=mem_id,
                            topic=topic,
                            content=lines[3] if len(lines) > 3 else "",
                            tags=[]
                        ))
            except Exception:
                continue
        return memories[:limit]


@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    handler: Any = None  # 可调用对象
    required_params: List[str] = field(default_factory=list)
    enabled: bool = True


class SkillRegistry:
    """技能注册表"""
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        """注册内置技能"""
        # 文献检索
        self.skills["arxiv"] = Skill(
            name="arxiv",
            description="arXiv 文献检索",
            required_params=["query"]
        )
        
        # 语义搜索
        self.skills["semantic_scholar"] = Skill(
            name="semantic_scholar",
            description="Semantic Scholar 学术搜索",
            required_params=["query"]
        )
        
        # Python执行
        self.skills["python_exec"] = Skill(
            name="python_exec",
            description="安全 Python 代码执行",
            required_params=["code"]
        )
        
        # Bash执行
        self.skills["bash"] = Skill(
            name="bash",
            description="Shell 命令执行",
            required_params=["command"]
        )
        
        # Markdown排版
        self.skills["markdown"] = Skill(
            name="markdown",
            description="Markdown 文档排版",
            required_params=["content"]
        )
        
        # LaTeX排版
        self.skills["latex"] = Skill(
            name="latex",
            description="LaTeX 文档生成",
            required_params=["content"]
        )
    
    def register(self, skill: Skill) -> None:
        """注册技能"""
        self.skills[skill.name] = skill
    
    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(name)
    
    def list_enabled(self) -> List[Skill]:
        """列出启用的技能"""
        return [s for s in self.skills.values() if s.enabled]
    
    def execute(self, name: str, **params) -> Any:
        """执行技能"""
        skill = self.skills.get(name)
        if not skill or not skill.enabled:
            return {"error": f"Skill {name} not found or disabled"}
        
        # 检查参数
        missing = [p for p in skill.required_params if p not in params]
        if missing:
            return {"error": f"Missing params: {missing}"}
        
        # 这里可以扩展为真正的Skill执行
        return {"status": "ok", "skill": name, "params": params}


class RAGContextBuilder:
    """RAG 上下文构建器"""
    
    def __init__(self, memory_bank: LocalMemoryBank, top_k: int = 3):
        self.memory_bank = memory_bank
        self.top_k = top_k
    
    def build_context(self, query: str) -> str:
        """构建注入上下文"""
        memories = self.memory_bank.search(query, limit=self.top_k)
        
        if not memories:
            return ""
        
        context_parts = ["### 历史经验参考"]
        for mem in memories:
            context_parts.append(f"**{mem.topic}** ({mem.created_at.strftime('%Y-%m-%d')})")
            context_parts.append(mem.content)
            context_parts.append("")
        
        return "\n".join(context_parts)


if __name__ == "__main__":
    # 测试
    bank = LocalMemoryBank("./memory_bank")
    
    # 保存
    mem_id = bank.save(
        topic="PET回收实验",
        content="使用乙二醇解聚PET，催化剂选用醋酸锌，温度160°C，产率95%",
        tags=["pet", "化学回收"]
    )
    print(f"保存记忆: {mem_id}")
    
    # 搜索
    results = bank.search("PET")
    print(f"找到 {len(results)} 条记忆")
    
    # 技能
    registry = SkillRegistry()
    for skill in registry.list_enabled():
        print(f"技能: {skill.name} - {skill.description}")