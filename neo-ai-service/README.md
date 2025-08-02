# Neo AI Service

AI service module for Neo Framework, providing unified access to multiple AI models through high-performance IPC communication.

## ✨ Core Features

- 🖥️ **Local Model Support** - Integrated with Ollama for offline operation
- ☁️ **Cloud Model Support** - Access mainstream AI models via OpenRouter
- 🔄 **Unified API** - Same interface for different models
- 🚀 **High Performance** - Efficient IPC-based communication
- 🛡️ **Intelligent Routing** - Auto-select best model based on task
- 📦 **Modular Design** - Easy to extend and maintain

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Neo Framework (neo-framework.exe)
- Ollama (for local models)
- Windows OS

### One-Click Start

```bash
# Start all services
.\start-ai-service.bat

# Stop all services
.\stop-all-services.bat
```

### Test Services

```bash
# Test local model (Ollama)
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma3:12b", "messages": [{"role": "user", "content": "Hello"}]}'

# Test cloud model (OpenRouter)
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

# Neo AI 服务

基于 Neo Framework 的智能 AI 服务模块，通过高性能 IPC 通信提供多种 AI 模型的统一访问接口。

## 🏗️ Neo Framework 架构

Neo AI Service 是 Neo Framework 生态系统的核心组件之一，采用微服务架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端应用                              │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────┴───────────────────────────────────┐
│                   Neo Framework 核心                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │ HTTP Gateway│  │Service Registry│ │ Load Balancer   │    │
│  └──────┬──────┘  └───────┬──────┘  └────────┬────────┘    │
│         │                  │                   │              │
│  ┌──────┴──────────────────┴──────────────────┴────────┐    │
│  │              IPC Transport Layer (9999)              │    │
│  └──────┬──────────────────┬──────────────────┬────────┘    │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                   │
    ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
    │AI Service │      │DB Service │      │Auth Service│
    └───────────┘      └───────────┘      └───────────┘
```

### 核心组件说明

1. **Neo Framework 核心**
   - HTTP Gateway (8080端口)：处理外部 HTTP 请求
   - Service Registry：服务注册与发现
   - Load Balancer：负载均衡和路由
   - IPC Transport：高性能进程间通信层

2. **AI Service 架构**
   ```
   AI Service
   ├── IPC Client         # 与框架通信
   ├── Service Core       # 核心服务逻辑
   ├── Model Adapters     # 模型适配器层
   │   ├── Ollama        # 本地模型
   │   └── OpenRouter    # 云端模型
   ├── Handlers          # 请求处理器
   └── Advanced Features # 高级功能
       ├── Cache        # 缓存系统
       ├── RateLimiter  # 限流器
       ├── Router       # 智能路由
       └── Monitor      # 性能监控
   ```

## 📡 IPC 通信协议

Neo Framework 使用自定义的二进制 IPC 协议，确保高性能和低延迟：

### 消息格式
```
[消息长度:4字节][消息类型:1字节][消息内容:N字节]

消息内容结构：
- ID (变长字符串)
- Service (变长字符串)  
- Method (变长字符串)
- Metadata (JSON)
- Data (二进制/JSON)
```

### 消息类型
- `REQUEST (1)`: 客户端请求
- `RESPONSE (2)`: 服务响应
- `REGISTER (3)`: 服务注册
- `HEARTBEAT (4)`: 心跳保持
- `ERROR (5)`: 错误消息

### 通信流程
1. **服务启动**: AI Service 连接到 Neo Framework (localhost:9999)
2. **服务注册**: 发送 REGISTER 消息，注册服务能力
3. **请求处理**: 接收 REQUEST，处理后返回 RESPONSE
4. **心跳维持**: 每30秒发送 HEARTBEAT 保持连接

## 🔧 详细配置

### 完整配置示例 (`config/ai_service.yaml`)

```yaml
# 服务基础配置
service:
  name: "ai-service"
  version: "1.0.0"
  log_level: "INFO"

# IPC 连接配置
ipc:
  host: "localhost"
  port: 9999
  heartbeat_interval: 30
  reconnect_attempts: 3

# AI 提供商配置
providers:
  # 本地模型 (Ollama)
  ollama:
    api_base: "http://localhost:11434"
    timeout: 60
    models:
      - "gemma3:12b"
      - "llama3:8b"
      - "codellama:13b"
    
  # 云端模型 (OpenRouter)
  openrouter:
    api_key: "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"
    api_base: "https://openrouter.ai/api/v1"
    timeout: 60
    extra_headers:
      HTTP-Referer: "http://localhost:9999"
      X-Title: "Neo AI Service"

# 默认参数
defaults:
  chat_model: "gemma3:12b"  # 优先使用本地模型
  temperature: 0.7
  max_tokens: null

# 高级功能配置（已实现，待集成）
cache:
  enabled: true
  max_memory_size: 104857600  # 100MB
  ttl: 3600                   # 1小时

rate_limiter:
  enabled: true
  global_rate: 1000    # 每分钟
  client_rate: 100     # 每客户端每分钟

router:
  enabled: true
  prefer_local: true   # 优先本地模型
  cost_sensitive: true # 成本敏感

monitoring:
  enabled: true
  export_interval: 60  # 秒
```

## 📦 安装部署

### 1. 环境准备

```bash
# 1. 安装 Python
# 下载 Python 3.9+ 并安装

# 2. 安装 Ollama (可选，用于本地模型)
# 从 https://ollama.ai 下载并安装

# 3. 克隆项目
git clone [repository-url]
cd neoAI
```

### 2. 依赖安装

```bash
cd neo-ai-service
pip install -r requirements.txt
```

### 3. 模型准备

```bash
# 下载推荐的本地模型
ollama pull gemma3:12b

# 查看已安装模型
ollama list
```

### 4. 配置修改

编辑 `config/ai_service.yaml`：
- 如需使用自己的 OpenRouter API Key，替换相应配置
- 调整模型偏好和默认参数

## 🔌 API 详细说明

### 1. 聊天接口

**端点**: `POST /api/ai-service/chat`

**请求格式**:
```json
{
  "model": "gemma3:12b",              // 模型名称
  "messages": [                       // 对话历史
    {
      "role": "system",               // 可选：系统提示
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "你好，请介绍一下自己"
    }
  ],
  "temperature": 0.7,                 // 可选：创造性程度 (0-2)
  "max_tokens": 1000,                 // 可选：最大生成长度
  "stream": false                     // 可选：流式响应
}
```

**响应格式**:
```json
{
  "status": "success",
  "data": {
    "content": "你好！我是一个AI助手...",
    "model": "gemma3:12b",
    "finish_reason": "stop",
    "usage": {
      "prompt_tokens": 15,
      "completion_tokens": 50,
      "total_tokens": 65,
      "total_cost": 0.0              // 本地模型费用为0
    }
  },
  "adapter_name": "ollama"           // 使用的适配器
}
```

### 2. 健康检查接口

**端点**: `POST /api/ai-service/health`

**响应示例**:
```json
{
  "status": "success",
  "data": {
    "healthy": true,
    "service": "ai-service",
    "version": "1.0.0",
    "adapters": ["ollama", "openrouter"],
    "message": "AI Service is running"
  }
}
```

### 3. 模型列表接口

**端点**: `POST /api/ai-service/list_models`

**响应示例**:
```json
{
  "status": "success",
  "data": {
    "providers": {
      "ollama": {
        "available": true,
        "models": ["gemma3:12b", "llama3:8b"],
        "base_url": "http://localhost:11434"
      },
      "openrouter": {
        "available": true,
        "models": ["openai/gpt-3.5-turbo", "anthropic/claude-3-haiku"],
        "requires_auth": true
      }
    },
    "defaults": {
      "chat_model": "gemma3:12b",
      "temperature": 0.7
    }
  }
}
```

## 🎯 使用场景

### 1. 本地优先策略
适合隐私敏感或离线环境：
```bash
# 使用本地 Ollama 模型处理敏感数据
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [{"role": "user", "content": "分析这份财务报告..."}]
  }'
```

### 2. 云端增强策略
需要更强能力时使用云端模型：
```bash
# 使用 OpenRouter 的免费模型
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "messages": [{"role": "user", "content": "写一篇关于量子计算的深度文章"}]
  }'
```

### 3. 代码生成场景
使用专门的代码模型：
```bash
# 使用 CodeLlama 生成代码
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "codellama:13b",
    "messages": [{"role": "user", "content": "实现一个二叉搜索树"}]
  }'
```

## 🛠️ 高级特性（已实现）

### 1. 智能缓存系统
- **LRU 缓存算法**: 自动淘汰最少使用的缓存项
- **TTL 支持**: 缓存项自动过期
- **压缩存储**: 减少内存占用
- **命中率统计**: 监控缓存效果

### 2. 限流保护
- **令牌桶算法**: 平滑的流量控制
- **多级限流**: 全局/客户端/模型级别
- **优先级队列**: VIP 客户端优先处理
- **自适应调整**: 根据负载动态调整

### 3. 智能路由
- **任务识别**: 自动识别代码、翻译、创意等任务类型
- **模型匹配**: 选择最适合的模型
- **成本优化**: 平衡性能和成本
- **故障转移**: 自动切换备用模型

### 4. 错误处理
- **重试机制**: 指数退避算法
- **熔断器**: 防止雪崩效应
- **降级策略**: 优雅降级
- **错误分析**: 详细的错误统计

### 5. 性能监控
- **系统指标**: CPU、内存、网络
- **服务指标**: QPS、延迟、错误率
- **模型指标**: 使用率、成功率
- **实时告警**: 阈值监控

## 🔍 故障诊断

### 常见问题解决

1. **端口占用错误**
   ```
   ERROR: Port 9999 is already in use!
   ```
   解决：运行 `.\stop-all-services.bat` 清理所有进程

2. **Ollama 连接失败**
   ```bash
   # 检查 Ollama 服务
   curl http://localhost:11434/api/tags
   
   # 重启 Ollama
   ollama serve
   ```

3. **OpenRouter 认证失败**
   - 检查 API Key 是否正确
   - 确认使用免费模型（带 `:free` 后缀）
   - 检查网络代理设置

4. **内存不足**
   - 减少缓存大小配置
   - 使用更小的模型
   - 增加系统内存

### 日志查看

```bash
# AI Service 日志
type neo-ai-service\ai_service.log

# 实时查看日志（PowerShell）
Get-Content neo-ai-service\ai_service.log -Wait -Tail 50
```

## 📈 性能优化建议

1. **模型选择**
   - 简单任务用小模型（gemma3:12b）
   - 复杂任务用大模型（云端模型）
   - 代码任务用专门模型（codellama）

2. **缓存策略**
   - 启用缓存减少重复请求
   - 设置合适的 TTL
   - 定期清理过期缓存

3. **并发控制**
   - 设置合理的限流值
   - 使用优先级队列
   - 监控系统负载

## 🤝 贡献指南

欢迎贡献代码和建议！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目是 Neo Framework 的一部分，遵循相同的许可证。

## 🙏 致谢

- Neo Framework 团队
- Ollama 项目
- OpenRouter 平台
- 所有贡献者

---

**项目状态**: 🟢 生产就绪 | **版本**: 1.0.0 | **最后更新**: 2025-08-02