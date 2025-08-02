# Neo AI Service 使用示例

## 服务信息

Neo AI Service 已注册到 Neo Framework，提供以下功能：

- **服务名称**: `ai-service`
- **支持的方法**: 
  - `chat` - AI对话
  - `generate_image` - 图像生成
  - `list_models` - 列出可用模型
  - `health` - 健康检查

## 快速开始

### 1. 启动所有服务

```bash
# 1. 启动 Neo Framework
start-neo.bat

# 2. 启动 Ollama (可选，用于本地模型)
ollama serve

# 3. 启动 AI Service
cd neo-ai-service
python src/main.py
```

### 2. 使用示例

#### Python 调用示例

```python
# 简单的聊天请求
{
    "method": "chat",
    "params": {
        "messages": [
            {"role": "user", "content": "你好！"}
        ],
        "model": "gemma3:12b"  # 本地模型
    }
}
```

#### 使用不同的模型

**本地模型 (Ollama)**:
```json
{
    "model": "gemma3:12b",
    "messages": [{"role": "user", "content": "Hello"}]
}
```

**OpenRouter GPT-3.5**:
```json
{
    "model": "openai/gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
}
```

**OpenRouter Claude**:
```json
{
    "model": "anthropic/claude-3-haiku",
    "messages": [{"role": "user", "content": "Hello"}]
}
```

## 支持的模型

### 本地模型 (Ollama)
- `gemma3:12b` - Google Gemma 12B
- `llama2` - Meta Llama 2
- `mistral` - Mistral 7B
- `codellama` - Code Llama

### OpenRouter 模型
- **OpenAI**: `openai/gpt-4o`, `openai/gpt-3.5-turbo`
- **Anthropic**: `anthropic/claude-3-opus`, `anthropic/claude-3-haiku`
- **Google**: `google/gemini-pro`
- **Meta**: `meta-llama/llama-3-8b-instruct`
- **Mistral**: `mistralai/mistral-7b-instruct`
- 还有300+更多模型...

## 完整的调用流程

1. 客户端连接到 Neo Framework (端口 9999)
2. 发送 IPC 请求到 `ai-service`
3. AI Service 根据模型选择合适的适配器
4. 返回 AI 响应

## 错误处理

如果遇到错误，响应格式如下：
```json
{
    "status": "error",
    "error": "错误描述"
}
```

## 测试

运行测试脚本：
```bash
# 测试 IPC 调用
python test_ai_service_ipc.py

# 测试特定适配器
cd neo-ai-service
python test_ollama.py
python test_openrouter_new.py
```