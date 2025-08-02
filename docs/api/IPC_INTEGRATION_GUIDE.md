# Neo AI Service IPC 调用指南

## 概述

Neo AI Service 是一个基于 Neo Framework 的 AI 服务，支持通过 IPC (进程间通信) 协议与多种 AI 模型进行交互。本文档详细介绍如何通过 IPC 调用 AI 服务。

## 服务架构

```
┌─────────────────┐     IPC      ┌─────────────────┐     HTTP     ┌─────────────────┐
│   AI Service    │ ◄──────────► │  Neo Framework  │ ◄──────────► │     Client      │
│ (Python Service)│   Port 9999  │   (Go Server)   │   Port 8080 │  (Application)  │
└─────────────────┘              └─────────────────┘              └─────────────────┘
         │
         ▼
┌─────────────────┐
│   AI Adapters   │
├─────────────────┤
│ • Ollama        │
│ • OpenRouter    │
│ • OpenAI        │
└─────────────────┘
```

## 快速开始

### 1. 启动服务

#### 启动 Neo Framework
```bash
.\neo-framework.exe -ipc :9999
```

#### 启动 AI Service
```bash
cd neo-ai-service
python src/main.py
```

### 2. 验证服务状态

```bash
# 健康检查
curl -X POST http://localhost:8080/api/ai-service/health -H "Content-Type: application/json" -d "{}"

# 列出可用模型
curl -X POST http://localhost:8080/api/ai-service/list_models -H "Content-Type: application/json" -d "{}"
```

## API 接口

### 1. Chat 接口

**端点**: `POST /api/ai-service/chat`

**请求格式**:
```json
{
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Hello, how are you?"
        }
    ],
    "model": "gemma3:12b",
    "temperature": 0.7,
    "max_tokens": 1000
}
```

**响应格式**:
```json
{
    "status": "success",
    "data": {
        "content": "I'm doing well, thank you! How can I help you today?",
        "model": "gemma3:12b",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 15,
            "total_tokens": 35,
            "total_cost": 0.0
        }
    }
}
```

**示例调用**:
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "model": "gemma3:12b"
  }'
```

### 2. List Models 接口

**端点**: `POST /api/ai-service/list_models`

**请求格式**:
```json
{}
```

**响应格式**:
```json
{
    "status": "success",
    "data": {
        "models": [
            {
                "provider": "ollama",
                "models": ["gemma3:12b", "llama3:8b"]
            },
            {
                "provider": "openrouter",
                "models": ["gpt-3.5-turbo", "gpt-4", "claude-3-opus"]
            }
        ]
    }
}
```

### 3. Health 接口

**端点**: `POST /api/ai-service/health`

**请求格式**:
```json
{}
```

**响应格式**:
```json
{
    "status": "healthy",
    "timestamp": "2025-08-01T10:30:45Z"
}
```

## 支持的 AI 提供商

### 1. Ollama (本地模型)
- **模型**: gemma3:12b, llama3:8b, codellama 等
- **特点**: 免费、本地运行、隐私安全
- **配置**: 需要本地运行 Ollama 服务

### 2. OpenRouter
- **模型**: GPT-3.5/4, Claude, Llama 等多种模型
- **特点**: 统一 API、多模型支持
- **配置**: 需要 API Key

### 3. OpenAI
- **模型**: GPT-3.5-turbo, GPT-4 等
- **特点**: 官方 API、稳定可靠
- **配置**: 需要 API Key

## 配置文件

AI Service 配置文件位于: `neo-ai-service/config/ai_service.yaml`

```yaml
service:
  name: ai-service
  version: 1.0.0

ipc:
  host: localhost
  port: 9999

providers:
  ollama:
    api_base: http://localhost:11434
    default_model: gemma3:12b
    
  openrouter:
    api_key: ${OPENROUTER_API_KEY}
    api_base: https://openrouter.ai/api/v1
    default_model: gpt-3.5-turbo
    
  openai:
    api_key: ${OPENAI_API_KEY}
    api_base: https://api.openai.com/v1
    default_model: gpt-3.5-turbo

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 使用示例

### Python 客户端示例

```python
import requests
import json

# AI 服务地址
AI_SERVICE_URL = "http://localhost:8080/api/ai-service"

def chat_with_ai(message, model="gemma3:12b"):
    """与 AI 进行对话"""
    response = requests.post(
        f"{AI_SERVICE_URL}/chat",
        json={
            "messages": [{"role": "user", "content": message}],
            "model": model
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("status") == "success":
            return result["data"]["content"]
    
    return None

# 使用示例
response = chat_with_ai("Hello, what's the weather like today?")
print(f"AI Response: {response}")
```

### Go 客户端示例

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

type ChatRequest struct {
    Messages []Message `json:"messages"`
    Model    string    `json:"model"`
}

type Message struct {
    Role    string `json:"role"`
    Content string `json:"content"`
}

func chatWithAI(message, model string) (string, error) {
    reqBody := ChatRequest{
        Messages: []Message{
            {Role: "user", Content: message},
        },
        Model: model,
    }
    
    jsonData, _ := json.Marshal(reqBody)
    
    resp, err := http.Post(
        "http://localhost:8080/api/ai-service/chat",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    
    if err != nil {
        return "", err
    }
    defer resp.Body.Close()
    
    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    
    if data, ok := result["data"].(map[string]interface{}); ok {
        if content, ok := data["content"].(string); ok {
            return content, nil
        }
    }
    
    return "", fmt.Errorf("unexpected response format")
}
```

## 故障排查

### 常见问题

1. **服务无法注册**
   - 检查 Neo Framework 是否正常运行
   - 确认 IPC 端口 (9999) 没有被占用
   - 查看日志中的注册错误信息

2. **调用返回 404**
   - 确认 AI Service 已成功注册
   - 检查服务名称是否正确 (ai-service)

3. **AI 模型不响应**
   - Ollama: 确认 `ollama serve` 正在运行
   - OpenRouter/OpenAI: 检查 API Key 是否正确配置

4. **超时错误**
   - 增加请求超时时间
   - 检查模型是否已下载 (Ollama)

### 日志位置

- Neo Framework 日志: 控制台输出
- AI Service 日志: 控制台输出

### 端口检查

```bash
# 检查 Neo Framework HTTP 端口
netstat -an | findstr :8080

# 检查 IPC 端口
netstat -an | findstr :9999

# 检查 Ollama 端口
netstat -an | findstr :11434
```

## 性能优化

1. **使用本地模型**: Ollama 模型运行在本地，响应速度快
2. **模型预加载**: 首次调用会加载模型，后续调用会更快
3. **批量请求**: 对于多个请求，考虑使用批量处理
4. **缓存响应**: 对于相同的输入，可以缓存响应结果

## 安全建议

1. **API Key 管理**: 使用环境变量存储 API Key，不要硬编码
2. **访问控制**: 在生产环境中添加认证和授权机制
3. **输入验证**: 验证用户输入，防止注入攻击
4. **日志脱敏**: 避免在日志中记录敏感信息

## 扩展开发

### 添加新的 AI 提供商

1. 在 `adapters` 目录创建新的适配器文件
2. 继承 `BaseAdapter` 类
3. 实现 `chat` 和 `list_models` 方法
4. 在 `main.py` 中注册新适配器

### 添加新的 API 端点

1. 在 `handlers` 目录创建新的处理器
2. 实现处理逻辑
3. 在服务初始化时注册处理器

## 总结

Neo AI Service 提供了一个灵活、可扩展的 AI 服务框架，通过 IPC 协议与 Neo Framework 集成，支持多种 AI 模型和提供商。通过统一的 HTTP API，客户端可以方便地调用各种 AI 功能。