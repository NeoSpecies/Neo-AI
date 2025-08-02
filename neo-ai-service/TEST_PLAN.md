# Neo AI Service 全面测试计划

## 测试环境准备

### 1. 启动服务
```bash
# 1. 启动 Neo Framework
cd neo-framework
go run cmd/neo/main.go

# 2. 启动 AI Service
cd neo-ai-service
python src/main.py
```

### 2. 确保 Ollama 运行
```bash
# 检查 Ollama 服务
curl http://localhost:11434/api/tags
```

## 测试用例

### 一、基础功能测试

#### 1.1 本地 Ollama 模型测试
```bash
# 测试本地 gemma3:12b 模型
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "你好，请用中文回答：什么是人工智能？"}
    ]
  }'
```

#### 1.2 OpenRouter 模型测试
```bash
# 测试 OpenRouter 免费模型
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "messages": [
      {"role": "user", "content": "Hello, what is AI?"}
    ]
  }'
```

### 二、缓存系统测试

#### 2.1 缓存命中测试
```bash
# 第一次请求（缓存未命中）
echo "=== First request (cache miss) ==="
time curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ]
  }'

# 第二次相同请求（缓存命中）
echo -e "\n=== Second request (cache hit) ==="
time curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ]
  }'
```

### 三、限流器测试

#### 3.1 批量请求测试
```bash
# 快速发送20个请求测试限流
echo "=== Rate limiting test ==="
for i in {1..20}; do
  echo "Request $i:"
  curl -X POST http://localhost:8080/v1/chat \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gemma3:12b",
      "messages": [
        {"role": "user", "content": "Test request '$i'"}
      ]
    }' &
done
wait
```

### 四、智能路由测试

#### 4.1 代码任务路由测试
```bash
# 应该路由到代码模型
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a Python function to sort a list"}
    ]
  }'
```

#### 4.2 创意任务路由测试
```bash
# 应该路由到创意模型
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a creative story about a robot"}
    ]
  }'
```

### 五、错误处理测试

#### 5.1 无效模型测试
```bash
# 测试错误处理和重试机制
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "invalid-model-name",
    "messages": [
      {"role": "user", "content": "Test error handling"}
    ]
  }'
```

#### 5.2 空消息测试
```bash
# 测试参数验证
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:12b",
    "messages": []
  }'
```

### 六、性能监控测试

#### 6.1 健康检查
```bash
# 获取服务健康状态和组件统计
curl http://localhost:8080/health | python -m json.tool
```

#### 6.2 性能指标
```bash
# 获取详细性能指标
curl http://localhost:8080/metrics | python -m json.tool
```

### 七、并发测试

#### 7.1 混合模型并发测试
```bash
# 同时测试本地和云端模型
echo "=== Concurrent mixed model test ==="

# 本地模型请求
for i in {1..5}; do
  curl -X POST http://localhost:8080/v1/chat \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gemma3:12b",
      "messages": [{"role": "user", "content": "Local test '$i'"}]
    }' &
done

# OpenRouter 模型请求
for i in {1..5}; do
  curl -X POST http://localhost:8080/v1/chat \
    -H "Content-Type: application/json" \
    -d '{
      "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
      "messages": [{"role": "user", "content": "Cloud test '$i'"}]
    }' &
done

wait
```

### 八、模型列表测试

#### 8.1 列出所有可用模型
```bash
curl http://localhost:8080/v1/models | python -m json.tool
```

## 预期结果

1. **基础功能**: 本地和云端模型都应正常响应
2. **缓存系统**: 第二次相同请求应明显更快
3. **限流器**: 超过限制的请求应返回限流错误
4. **智能路由**: 根据任务类型选择合适的模型
5. **错误处理**: 优雅处理各种错误情况
6. **性能监控**: 显示详细的系统和服务指标
7. **并发处理**: 同时处理多个请求不出错

## 测试脚本

将所有测试整合为一个脚本：`test_all.sh`