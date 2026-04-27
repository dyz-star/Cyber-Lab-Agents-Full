# 🏢 Cyber-Lab-Agents 多智能体科研协作系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-green?style=flat&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-blue?style=flat&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License">
</p>

> 🧪 赛博课题组 - 基于 Multi-Agent 的高分子科研自动化协作系统

---

## 📋 目录

1. [项目愿景](#项目愿景)
2. [架构详解](#架构详解)
3. [科研实战指南](#科研实战指南)
4. [部署手册](#部署手册)
5. [API 参考](#api-参考)
6. [常见问题](#常见问题)

---

## 🎯 项目愿景

### 科研痛点

当前高分子化学研究面临以下挑战：

| 痛点 | 描述 | 本系统解决方案 |
|------|------|----------------|
| **文献调研效率低** | 聚酯回收、聚合物解聚领域文献分散，获取成本高 | PhD_1 自动检索 arXiv/Semantic Scholar |
| **实验逻辑不闭环** | 单体共聚研究需反复修改方案，缺乏版本追踪 | Workflow Engine 任务流转 + 记忆库 |
| **团队协作混乱** | 导师-小导-博士三级汇报关系不清 | 权限矩阵 + 越级拦截 |
| **情绪管理缺位** | 科研压力大，成员动力不足 | Sycophant Agent PUA/鼓励机制 |

### 核心价值

- **自动化**：文献调研、代码执行、文档排版全自动化
- **规范化**：权限清晰、流程闭环、状态可追溯
- **轻量化**：单用户、本地存储、Docker 一键部署
- **可扩展**：模块化设计，支持 Skill 插件扩展

---

## 🏗️ 架构详解

### 系统拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                      父皇 (Mentor)                           │
│                    任务入口 / 最终审核                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  小导1        │  │  小导2        │  │  小导3        │
│ (科研任务)    │  │ (日常任务)    │  │ (备用)        │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  博士1        │  │  博士2        │  │  博士3        │
│ (文献检索)    │  │ (代码执行)    │  │ (文档排版)    │
└───────────────┘  └───────────────┘  └───────────────┘

        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
                  ┌───────────────┐
                  │    马屁精      │
                  │ (情绪管理)     │
                  └───────────────┘
```

### 8 Agent 职责矩阵

| Agent | 角色 | 职责描述 | 可发送至 | 可接收自 |
|-------|------|----------|----------|----------|
| **Mentor** | 导师 | 系统入口，任务派发与终审 | Junior_PI_1/2/3, Sycophant | Junior_PI_1/2/3, Sycophant |
| **Junior_PI_1** | 小导1 | 科研任务专用，复杂任务触发竞标 | Mentor, PhD_1, Sycophant | Mentor, PhD_1 |
| **Junior_PI_2** | 小导2 | 日常任务专用，直接下派 | Mentor, PhD_2, Sycophant | Mentor, PhD_2 |
| **Junior_PI_3** | 小导3 | 备用小导，特殊任务 | Mentor, PhD_3, Sycophant | Mentor, PhD_3 |
| **PhD_1** | 博士1 | 文献检索专家 | Junior_PI_1 | Junior_PI_1 |
| **PhD_2** | 博士2 | 代码执行专家 | Junior_PI_2 | Junior_PI_2 |
| **PhD_3** | 博士3 | 文档排版专家 | Junior_PI_3 | Junior_PI_3 |
| **Sycophant** | 马屁精 | 双向情绪管理，向上陪聊，向下 PUA | Mentor, Junior_PI_1/2/3 | Mentor, Junior_PI_1/2/3 |

### PUA 触发机制

当任务被导师打回 **≥2 次** 时，马屁精自动介入：

```
导师打回任务 → retry_count >= 2 → trigger_pua() 
    ↓
生成 PUA 话术:
  - "小导啊，这个任务怎么搞的？导师已经打回一次了..."
  - "进度太慢了，其他组都在赶进度，我们不能掉队啊。"
  - "这个产出有点水啊，要不要我再带带你？"
    ↓
异步发送给对应 Junior_PI → 触发团队压力传导
```

### 工作流状态机

```
PENDING → IN_PROGRESS → REVIEW → COMPLETED
    ↓         ↓            ↓
  REVISION ←─────────────┘
    ↓
  FAILED (max_retries=3 熔断)
```

---

## 🔬 科研实战指南

### 场景一：聚酯化学回收文献调研

**任务描述**：
> 调研 PET 化学回收的最新进展，重点关注乙二醇解聚催化体系

**操作流程**：

```bash
# 1. 通过 API 创建任务
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "PET化学回收文献调研",
    "description": "调研PET化学回收的最新进展，重点关注乙二醇解聚催化体系"
  }'

# 2. 系统自动路由：Mentor → Junior_PI_1 (科研) → PhD_1 (文献)
# 3. PhD_1 调用 arxiv/semantic_scholar 技能检索
# 4. 结果存入记忆库，供后续参考
```

### 场景二：聚合物共聚实验代码

**任务描述**：
> 编写 Python 脚本模拟 PLA-PHB 共聚反应动力学

**操作流程**：

```bash
# 自动路由：Mentor → Junior_PI_2 (日常) → PhD_2 (代码)
# PhD_2 调用 python_exec 技能执行代码
```

### 场景三：论文润色排版

**任务描述**：
> 将实验数据整理为 LaTeX 格式的论文草稿

**操作流程**：

```bash
# 自动路由：Mentor → Junior_PI_3 → PhD_3 (文档)
# PhD_3 调用 latex 技能排版
```

---

## 🚀 部署手册

### 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.11 | 3.12 |
| Docker | 24.0 | 25.0+ |
| Docker Compose | 2.24 | 2.25+ |

### 快速部署（Docker 推荐）

```bash
# 1. 克隆或下载代码
cd Cyber-Lab-Agents-Full

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 一键启动
docker-compose up -d

# 4. 验证部署
curl http://localhost:8000/health
```

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env

# 3. 启动服务
python src/main.py
# 或
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 环境变量详解

```bash
# ====================
# Agent 模型配置
# ====================
MENTOR_MODEL=gpt-4o
MENTOR_API_KEY=sk-your-openai-key

JUNIOR_PI_1_MODEL=gpt-4o
JUNIOR_PI_1_API_KEY=sk-your-openai-key
# ... 其他 Agent 类似

# ====================
# 飞书机器人（可选）
# ====================
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=your-secret
FEISHU_VERIFY_TOKEN=your-token
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# ====================
# 服务配置
# ====================
DASHBOARD_PORT=8000
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 状态看板 | http://localhost:8000/dashboard |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| 飞书 Webhook | http://localhost:8000/webhook/feishu |

---

## 📚 API 参考

### 任务管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/tasks` | 列出所有任务 |
| POST | `/api/tasks` | 创建新任务 |
| POST | `/api/tasks/update` | 更新任务状态（approve/reject/submit） |

### Agent 管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/agents` | 列出所有 Agent |

### 记忆库

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/memory?q=keyword` | 搜索记忆 |

### 技能

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/skills` | 列出可用技能 |

---

## ❓ 常见问题

### Q1: 如何修改 Agent 模型？

编辑 `.env` 文件中的 `*_MODEL` 和 `*_API_KEY` 参数。

### Q2: PUA 消息如何关闭？

在 `config/agents.yaml` 中设置 `pua.enabled: false`，或在代码中设置 `engine.pua_enabled = False`。

### Q3: 如何添加新的技能？

在 `src/memory_skills.py` 的 `SkillRegistry` 中注册新的 Skill。

### Q4: 飞书机器人如何配置？

1. 创建飞书应用：https://open.feishu.cn/
2. 添加机器人，获取 App ID/Secret
3. 配置 Webhook 回调 URL
4. 填入 `.env`

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<p align="center">
  <strong>🧪 赛博课题组 · 让科研更智能</strong><br>
  Built with ❤️ for Polymer Science
</p>