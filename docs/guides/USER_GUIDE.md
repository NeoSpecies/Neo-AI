# Neo AI Service 使用指南

## 概述

Neo AI Service 是基于 Neo Framework 的 AI 服务，支持同时使用本地 Ollama 模型和云端 OpenRouter 服务。

## 快速开始

### 1. 启动服务

**推荐方法（一键启动）：**
```bash
.\start-ai-service.bat
```

该脚本会自动：
- 检查端口可用性
- 启动 Neo Framework
- 启动 AI Service
- 验证服务状态

**手动启动（如需调试）：**
```bash
# 终端1 - 启动 Neo Framework
.\neo-framework.exe

# 终端2 - 启动 AI Service
cd neo-ai-service
python src\main.py
```

### 2. 测试服务

**健康检查：**
```bash
curl -X POST http://localhost:8080/api/ai-service/health -H "Content-Type: application/json" -d "{}"
```

**使用 Ollama（本地免费）：**
```bash
curl -X POST http://localhost:8080/api/ai-service/chat -H "Content-Type: application/json" -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}], \"model\": \"gemma3:12b\"}"
```

**使用 OpenRouter（云端付费）：**
```bash
curl -X POST http://localhost:8080/api/ai-service/chat -H "Content-Type: application/json" -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}], \"model\": \"openai/gpt-3.5-turbo\"}"
```

### 3. 停止服务

```bash
.\stop-all-services.bat
```

该脚本会：
- 停止所有 Python 进程
- 停止 Neo Framework
- 清理占用的端口

## 支持的模型

### Ollama（本地模型）
- `gemma3:12b` - 通用对话模型
- `llama3:8b` - 轻量级模型
- `codellama:13b` - 代码生成模型

### OpenRouter（云端模型）
- `cognitivecomputations/dolphin-mistral-24b-venice-edition:free` - 免费模型（已测试可用）
- `openai/gpt-3.5-turbo` - 经济实惠的通用模型（需要账户余额）
- `openai/gpt-4` - 高级推理模型（需要账户余额）
- `anthropic/claude-3-haiku` - 快速响应模型（需要账户余额）
- `anthropic/claude-3-opus` - 强大的创意模型（需要账户余额）

## API 接口详情

### Chat 接口
**端点**: `POST /api/ai-service/chat`

**请求示例：**
```json
{
    "messages": [
        {
            "role": "user",
            "content": "你的问题"
        }
    ],
    "model": "gemma3:12b",
    "temperature": 0.7,
    "max_tokens": 1000
}
```

**响应示例：**
```json
{
    "status": "success",
    "data": {
        "content": "AI的回复",
        "model": "gemma3:12b",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "total_cost": 0.0
        }
    }
}
```

### List Models 接口
**端点**: `POST /api/ai-service/list_models`

列出所有可用的模型。

### Health 接口
**端点**: `POST /api/ai-service/health`

检查服务健康状态。

## 配置说明

配置文件位于：`neo-ai-service/config/ai_service.yaml`

主要配置项：
- **OpenRouter API Key**: 已配置在 yaml 文件中
- **Ollama API Base**: 默认为 `http://localhost:11434`
- **IPC 端口**: 默认为 9999

## 故障排查

1. **端口被占用错误**
   ```
   ERROR: Port 9999 is already in use!
   ```
   解决方法：运行 `.\stop-all-services.bat` 清理所有进程

2. **Ollama 模型不响应**
   - 确保 Ollama 服务正在运行
   - 检查模型是否已下载：
   ```bash
   ollama list
   # 如果没有 gemma3:12b，下载它：
   ollama pull gemma3:12b
   ```

3. **OpenRouter 401 错误**
   - 检查 `neo-ai-service/config/ai_service.yaml` 中的 API Key
   - 确保使用免费模型（带 `:free` 后缀）
   - 当前可用的免费模型：`cognitivecomputations/dolphin-mistral-24b-venice-edition:free`

4. **查看日志**
   - AI Service 日志：`neo-ai-service/ai_service.log`
   - Neo Framework：查看控制台输出

## 技术架构

```
客户端 → HTTP (8080) → Neo Framework → IPC (9999) → AI Service
                                                          ↓
                                                    Model Router
                                                    ↙         ↘
                                            Ollama Adapter   OpenRouter Adapter
```

## 最佳实践

1. **成本控制**：优先使用 Ollama 本地模型（免费）
2. **性能优化**：本地模型响应更快，适合实时应用
3. **隐私保护**：敏感数据使用本地 Ollama 模型处理

## 更新历史

### 2025-08-02 更新
1. ✅ 更新 OpenRouter API 密钥，免费模型测试通过
2. ✅ 改进启动脚本，增加端口检查和服务验证
3. ✅ 简化主程序结构，提高稳定性
4. ✅ 实现高级功能模块（缓存、限流、路由、监控）
5. ✅ 清理废弃文件，优化项目结构

### 2025-08-01 修复
1. ✅ IPC 消息类型定义匹配（REGISTER=3, REQUEST=1）
2. ✅ 服务元数据格式（capabilities 转为 JSON 字符串）
3. ✅ Chat handler 参数传递问题
4. ✅ 正确的 IPC 客户端实现

## 高级功能（已实现，待集成）

以下功能已完成代码实现，将在后续版本中集成：

- **缓存系统**：LRU 缓存，支持 TTL，减少重复请求
- **限流器**：令牌桶算法，支持多级限流
- **智能路由**：基于任务类型自动选择最佳模型
- **错误处理**：重试机制、熔断器、优雅降级
- **性能监控**：系统指标收集、性能分析

## 结论

Neo AI Service 核心功能已完全测试通过：
- ✅ 本地 Ollama 模型（免费、快速、隐私）
- ✅ 云端 OpenRouter 模型（新 API 密钥已验证）
- ✅ 统一的 API 接口
- ✅ 稳定的服务架构

系统运行稳定，可投入使用！