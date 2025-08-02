# Neo AI Service 手动测试指南

## 前置准备

### 1. 确保服务运行
```bash
# 1. 启动 Neo Framework（如果未运行）
neo-framework.exe

# 2. 启动 AI Service（新窗口）
cd neo-ai-service
python src/main_simple.py
```

### 2. 确认服务状态
等待看到以下日志：
- Neo Framework: `HTTP Gateway started on :8080`
- AI Service: `AI Service registered with Neo Framework`

## 手动测试方案

### 测试 1：服务健康检查 🏥

#### 1.1 检查 Neo Framework
```bash
curl http://localhost:8080/health
```
**预期结果**：
```json
{
  "status": "healthy",
  "time": "2025-08-02T..."
}
```

#### 1.2 检查 AI Service
```bash
curl http://localhost:8080/api/ai-service/health
```
**预期结果**：
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

### 测试 2：本地 AI 模型 (Ollama) 🖥️

#### 2.1 简单数学问题
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "What is 25 + 37?"}
    ]
  }'
```
**预期**：返回 "62" 或类似的正确答案

#### 2.2 中文对话测试
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "请用中文解释什么是人工智能，用简单的语言，50字以内"}
    ]
  }'
```
**预期**：返回简短的中文解释

#### 2.3 编程问题
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "Write a Python function to reverse a string"}
    ]
  }'
```
**预期**：返回 Python 代码

### 测试 3：云端 AI 模型 (OpenRouter) ☁️

#### 3.1 基础对话
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "messages": [
      {"role": "user", "content": "What is the weather like today?"}
    ]
  }'
```
**预期**：返回关于天气的回复（会说它不知道实时天气）

#### 3.2 创意写作
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "messages": [
      {"role": "user", "content": "Write a haiku about coding"}
    ]
  }'
```
**预期**：返回一首关于编程的俳句

### 测试 4：多轮对话 💬

```bash
# 第一轮
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "My name is Alice. Remember this."}
    ]
  }'

# 第二轮（包含上下文）
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "My name is Alice. Remember this."},
      {"role": "assistant", "content": "Hello Alice! I will remember your name. How can I help you today?"},
      {"role": "user", "content": "What is my name?"}
    ]
  }'
```
**预期**：第二轮应该记得名字是 Alice

### 测试 5：错误处理 ⚠️

#### 5.1 无效模型
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "invalid-model-xyz",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```
**预期**：返回错误信息

#### 5.2 空消息
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": []
  }'
```
**预期**：返回 "No messages provided" 错误

#### 5.3 缺少必要字段
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b"
  }'
```
**预期**：返回错误信息

### 测试 6：模型列表 📋

```bash
curl http://localhost:8080/api/ai-service/list_models
```
**预期**：返回可用模型列表和配置信息

### 测试 7：性能测试 ⚡

#### 7.1 响应时间测试
```bash
# 使用 time 命令测量响应时间
time curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ]
  }'
```
**预期**：
- Ollama: < 1秒
- OpenRouter: 1-3秒

#### 7.2 并发测试（可选）
在多个终端同时运行：
```bash
# 终端 1
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma3:12b", "messages": [{"role": "user", "content": "Count from 1 to 10"}]}'

# 终端 2
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma3:12b", "messages": [{"role": "user", "content": "List 5 colors"}]}'
```
**预期**：两个请求都应该成功返回

## 测试检查清单 ✅

- [ ] Framework 健康检查通过
- [ ] AI Service 健康检查通过
- [ ] Ollama 简单问题回答正确
- [ ] Ollama 中文对话正常
- [ ] Ollama 代码生成正常
- [ ] OpenRouter 基础对话正常
- [ ] OpenRouter 创意任务正常
- [ ] 多轮对话上下文保持
- [ ] 错误处理返回合理信息
- [ ] 模型列表显示正确
- [ ] 响应时间在预期范围内

## 故障排查 🔧

### 问题 1：连接被拒绝
- 检查服务是否运行：`ps aux | grep python`
- 查看日志：`cat neo-ai-service/ai_service_simple.log`

### 问题 2：404 错误
- 确认 URL 路径正确：`/api/ai-service/chat`
- 检查服务是否注册成功

### 问题 3：Ollama 不工作
- 确认 Ollama 服务运行：`curl http://localhost:11434/api/tags`
- 确认模型已下载：`ollama list`

### 问题 4：OpenRouter 401 错误
- 检查 API 密钥是否正确
- 确认使用的是免费模型

## 测试结果记录模板 📝

```
测试时间：_____________
测试人员：_____________

基础功能：
- [ ] 健康检查 (____ms)
- [ ] Ollama 对话 (____ms)
- [ ] OpenRouter 对话 (____ms)

功能测试：
- [ ] 中文支持
- [ ] 代码生成
- [ ] 多轮对话
- [ ] 错误处理

性能指标：
- Ollama 平均响应：____ms
- OpenRouter 平均响应：____ms
- 并发处理：正常/异常

问题记录：
_________________________
_________________________
```

## 高级测试（可选）🚀

### 1. 长文本处理
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "Please summarize the following text in 3 bullet points: [插入一段长文本]"}
    ]
  }'
```

### 2. 参数调整测试
```bash
curl -X POST http://localhost:8080/api/ai-service/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "Generate a random number"}
    ],
    "temperature": 0.1,
    "max_tokens": 50
  }'
```

祝测试顺利！如有任何问题，请查看日志文件获取详细信息。