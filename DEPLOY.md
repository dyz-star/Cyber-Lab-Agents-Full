# Cyber-Lab-Agents 部署指南

## 环境要求
- Python 3.11+
- Docker & Docker Compose

## 快速部署

### 1. 填写配置

```bash
cd Cyber-Lab-Agents-Full
cp .env.example .env
```

编辑 `.env` 文件，填入以下配置：

```bash
# ====================
# Agent 模型配置
# ====================
MENTOR_MODEL=gpt-4o
MENTOR_API_KEY=sk-your-openai-key-here

JUNIOR_PI_1_MODEL=gpt-4o
JUNIOR_PI_1_API_KEY=sk-your-openai-key-here

# ... 其他 Agent 配置类似

# ====================
# 飞书机器人配置
# ====================
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=your-feishu-app-secret
FEISHU_VERIFY_TOKEN=your-verify-token
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx

# ====================
# 服务配置
# ====================
DASHBOARD_PORT=8000
```

### 2. 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python src/main.py
# 或
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3. Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 状态看板 | http://localhost:8000/dashboard |
| API 文档 | http://localhost:8000/docs |
| 飞书 Webhook | http://your-server:8000/webhook/feishu |

## 飞书机器人配置

1. 创建飞书应用：https://open.feishu.cn/
2. 添加机器人，获取 App ID 和 App Secret
3. 配置 Webhook 回调地址
4. 将配置填入 `.env`

## 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 查看 Agent 列表
curl http://localhost:8000/api/agents
```

## 注意事项

1. **API Key 安全**：切勿将 `.env` 文件提交到版本控制
2. **端口占用**：确保 8000 端口未被占用
3. **生产环境**：建议使用 Nginx 反向代理 + HTTPS

---
**功成封卷，交付父皇！** 🎉