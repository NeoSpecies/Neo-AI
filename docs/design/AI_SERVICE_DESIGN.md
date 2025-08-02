# Neo AI Service 设计文档

## 1. 服务概述

### 1.1 背景与目标

Neo AI Service 是一个统一的AI模型接入服务，旨在为Neo Framework提供标准化的AI能力接口。通过该服务，框架内的其他服务和用户可以通过IPC协议调用各种AI模型，包括但不限于：

- 文本生成模型（GPT-4、Claude、文心一言等）
- 图像生成模型（DALL-E、Stable Diffusion、Midjourney等）
- 图像理解模型（GPT-4V、Claude Vision等）
- 语音识别与合成（Whisper、Azure Speech等）
- 嵌入向量模型（text-embedding-ada-002等）

### 1.2 核心特性

- **多模型支持**：通过统一接口支持多家AI服务商
- **多模态处理**：支持文本、图像、音频等多种输入输出格式
- **配置驱动**：通过配置文件即可添加新的AI模型
- **流式响应**：支持实时流式输出，提升用户体验
- **智能路由**：根据任务类型自动选择最合适的模型
- **成本控制**：内置使用量追踪和成本限制
- **缓存机制**：智能缓存减少重复调用
- **安全防护**：API密钥加密、内容过滤、访问控制

### 1.3 技术选型

**开发语言**: Python 3.9+

**选择理由**:
- AI生态系统最为完善（openai、anthropic、google-generativeai等官方SDK）
- 优秀的异步支持（asyncio）
- 丰富的多模态处理库（Pillow、opencv-python、librosa等）
- 成熟的流式处理支持
- 易于扩展和维护

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Neo Framework                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │Other Service│  │HTTP Gateway │  │   User App  │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                           │                                  │
│                    IPC Protocol                              │
│                           │                                  │
│  ┌───────────────────────┴────────────────────────────┐    │
│  │                  AI Service                          │    │
│  │  ┌─────────────────────────────────────────────┐   │    │
│  │  │            Service Core                      │   │    │
│  │  │  ┌─────────┐  ┌──────────┐  ┌───────────┐ │   │    │
│  │  │  │ Router   │  │ Cache    │  │ RateLimiter│ │   │    │
│  │  │  └────┬─────┘  └────┬─────┘  └─────┬─────┘ │   │    │
│  │  └───────┼──────────────┼──────────────┼───────┘   │    │
│  │          │              │              │            │    │
│  │  ┌───────┴──────────────┴──────────────┴────────┐  │    │
│  │  │           Model Adapter Layer                 │  │    │
│  │  │  ┌─────────┐ ┌──────────┐ ┌──────────────┐  │  │    │
│  │  │  │ OpenAI  │ │Anthropic │ │ Google/Baidu │  │  │    │
│  │  │  │ Adapter │ │ Adapter  │ │   Adapter    │  │  │    │
│  │  │  └────┬────┘ └────┬─────┘ └──────┬───────┘  │  │    │
│  │  └───────┼───────────┼───────────────┼──────────┘  │    │
│  └──────────┼───────────┼───────────────┼─────────────┘    │
└─────────────┼───────────┼───────────────┼───────────────────┘
              │           │               │
         ┌────┴────┐ ┌────┴─────┐  ┌─────┴──────┐
         │ OpenAI  │ │Anthropic │  │Google/Baidu│
         │   API   │ │   API    │  │    API     │
         └─────────┘ └──────────┘  └────────────┘
```

### 2.2 核心组件

#### 2.2.1 Service Core（服务核心）
- **请求处理器**: 接收和解析IPC请求
- **响应构建器**: 构建标准化响应
- **错误处理器**: 统一的错误处理和恢复机制
- **监控采集器**: 性能指标和日志收集

#### 2.2.2 Router（智能路由器）
- **任务分析**: 分析请求类型和需求
- **模型选择**: 根据任务特征选择最优模型
- **负载均衡**: 在多个可用模型间分配请求
- **故障转移**: 自动切换到备用模型

#### 2.2.3 Cache Manager（缓存管理器）
- **语义缓存**: 基于输入相似度的智能缓存
- **TTL管理**: 可配置的缓存过期策略
- **存储后端**: 支持内存、Redis、磁盘等

#### 2.2.4 Rate Limiter（限流器）
- **配额管理**: 用户/服务级别的配额控制
- **令牌桶算法**: 平滑的流量控制
- **优先级队列**: 重要请求优先处理

#### 2.2.5 Model Adapter（模型适配器）
- **统一接口**: 屏蔽不同API的差异
- **协议转换**: 请求/响应格式转换
- **特性适配**: 处理模型特有功能

### 2.3 数据流设计

```python
# 请求流程
1. IPC请求 → 请求验证 → 任务分析
2. 缓存检查 → 命中则返回缓存结果
3. 限流检查 → 超限则排队或拒绝
4. 模型选择 → 请求适配 → 调用外部API
5. 响应处理 → 缓存存储 → IPC响应

# 流式响应流程
1. 建立流式连接
2. 逐块接收数据 → 实时转发
3. 错误处理和断线重连
4. 完成后更新缓存
```

## 2.4 IPC协议集成

### 2.4.1 协议实现

AI服务严格遵循Neo Framework的二进制IPC协议规范：

```python
# 消息格式
[消息长度:4字节(小端序)][消息内容:N字节]

# 消息内容结构
[类型:1字节][ID长度:4字节][ID:N字节][服务名长度:4字节][服务名:N字节]
[方法名长度:4字节][方法名:N字节][元数据长度:4字节][元数据JSON:N字节]
[数据长度:4字节][数据:N字节]
```

### 2.4.2 服务注册

```python
class AIServiceIPCClient(NeoIPCClient):
    """AI服务IPC客户端"""
    
    async def register(self):
        """注册AI服务"""
        register_data = {
            "name": "ai-service",
            "metadata": {
                "version": "1.0.0",
                "protocol": "ipc",
                "language": "python",
                "capabilities": [
                    "chat", "generate_image", "analyze_image",
                    "transcribe_audio", "generate_speech", 
                    "create_embedding"
                ]
            }
        }
        
        msg = Message(
            msg_type=MessageType.REGISTER,
            id="",
            service="ai-service",
            method="",
            data=json.dumps(register_data).encode('utf-8'),
            metadata={}
        )
        await self._send_message(msg)
```

### 2.4.3 请求处理

```python
async def handle_ipc_request(self, msg: Message) -> Message:
    """处理IPC请求"""
    try:
        # 解析请求
        request_data = json.loads(msg.data.decode('utf-8'))
        method = msg.method
        params = request_data.get('params', {})
        
        # 路由到处理方法
        result = await self.route_request(method, params)
        
        # 构建响应
        response_data = {
            "status": "success",
            "data": result
        }
        
        return Message(
            msg_type=MessageType.RESPONSE,
            id=msg.id,  # 保持相同ID
            service="ai-service",
            method=msg.method,
            data=json.dumps(response_data).encode('utf-8'),
            metadata={}
        )
    except Exception as e:
        # 错误响应
        return Message(
            msg_type=MessageType.RESPONSE,
            id=msg.id,
            service="ai-service",
            method=msg.method,
            data=json.dumps({"error": str(e)}).encode('utf-8'),
            metadata={"error": "true"}
        )
```

### 2.4.4 流式响应实现

对于支持流式的方法，通过多个RESPONSE消息实现：

```python
async def handle_streaming_chat(self, msg: Message, params: dict):
    """流式对话处理"""
    request_id = msg.id
    
    # 流式发送响应块
    async for chunk in self.generate_stream(params):
        chunk_msg = Message(
            msg_type=MessageType.RESPONSE,
            id=request_id,
            service="ai-service",
            method="chat",
            data=json.dumps({
                "status": "streaming",
                "data": {"delta": chunk}
            }).encode('utf-8'),
            metadata={"streaming": "true"}
        )
        await self._send_message(chunk_msg)
    
    # 发送结束标记
    end_msg = Message(
        msg_type=MessageType.RESPONSE,
        id=request_id,
        service="ai-service",
        method="chat",
        data=json.dumps({
            "status": "stream_end",
            "data": {"usage": self.calculate_usage()}
        }).encode('utf-8'),
        metadata={"streaming": "true", "final": "true"}
    )
    await self._send_message(end_msg)
```

### 2.4.5 心跳维护

```python
async def heartbeat_loop(self):
    """心跳循环"""
    while True:
        await asyncio.sleep(30)
        heartbeat_msg = Message(
            msg_type=MessageType.HEARTBEAT,
            id="",
            service="ai-service",
            method="",
            data=b"",
            metadata={}
        )
        await self._send_message(heartbeat_msg)
```

## 3. 接口设计

### 3.1 服务注册

服务名称: `ai-service`

### 3.2 核心方法

#### 3.2.1 chat（对话生成）
```python
{
    "method": "chat",
    "params": {
        "messages": [
            {
                "role": "system|user|assistant",
                "content": "文本内容",
                "images": ["base64编码的图片"],  # 可选，多模态输入
                "audio": "base64编码的音频"       # 可选，语音输入
            }
        ],
        "model": "gpt-4",  # 可选，指定模型
        "stream": false,    # 是否流式响应
        "temperature": 0.7, # 可选，创造性参数
        "max_tokens": 1000, # 可选，最大输出长度
        "options": {        # 可选，模型特定参数
            "top_p": 0.9,
            "frequency_penalty": 0.0
        }
    },
    "request_id": "unique-request-id"
}

# 响应
{
    "status": "success",
    "data": {
        "content": "生成的文本",
        "model": "gpt-4",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_cost": 0.0015  # 美元
        },
        "finish_reason": "stop"
    }
}
```

#### 3.2.2 generate_image（图像生成）
```python
{
    "method": "generate_image",
    "params": {
        "prompt": "详细的图像描述",
        "negative_prompt": "不想要的元素",  # 可选
        "model": "dall-e-3",                # 可选
        "size": "1024x1024",                # 可选
        "quality": "hd",                    # 可选
        "style": "vivid",                   # 可选
        "n": 1                              # 生成数量
    }
}

# 响应
{
    "status": "success",
    "data": {
        "images": [
            {
                "url": "https://...",
                "base64": "base64编码的图片",
                "revised_prompt": "实际使用的提示词"
            }
        ],
        "model": "dall-e-3",
        "cost": 0.04
    }
}
```

#### 3.2.3 analyze_image（图像分析）
```python
{
    "method": "analyze_image",
    "params": {
        "images": ["base64图片数据"],
        "question": "关于图片的问题",
        "model": "gpt-4-vision-preview",  # 可选
        "detail": "high"                  # 可选，分析精度
    }
}
```

#### 3.2.4 transcribe_audio（语音识别）
```python
{
    "method": "transcribe_audio",
    "params": {
        "audio": "base64音频数据",
        "language": "zh",              # 可选
        "model": "whisper-1",          # 可选
        "format": "text|srt|vtt"       # 输出格式
    }
}
```

#### 3.2.5 generate_speech（语音合成）
```python
{
    "method": "generate_speech",
    "params": {
        "text": "要转换的文本",
        "voice": "alloy",              # 声音选择
        "model": "tts-1-hd",           # 可选
        "speed": 1.0                   # 语速
    }
}
```

#### 3.2.6 create_embedding（生成嵌入向量）
```python
{
    "method": "create_embedding",
    "params": {
        "input": ["文本1", "文本2"],
        "model": "text-embedding-ada-002"
    }
}
```

#### 3.2.7 list_models（列出可用模型）
```python
{
    "method": "list_models",
    "params": {
        "type": "chat|image|audio|embedding"  # 可选，过滤类型
    }
}
```

### 3.3 流式响应

对于支持流式的方法（如chat），响应将分多次发送：

```python
# 流式响应块
{
    "status": "streaming",
    "data": {
        "delta": "新增的内容片段",
        "index": 0  # 流索引
    }
}

# 流结束标记
{
    "status": "stream_end",
    "data": {
        "finish_reason": "stop",
        "usage": {...}
    }
}
```

## 4. 配置系统

### 4.1 主配置文件 (ai_service_config.yaml)

```yaml
service:
  name: "ai-service"
  version: "1.0.0"
  log_level: "INFO"
  
# 模型提供商配置
providers:
  openai:
    api_key: "${OPENAI_API_KEY}"  # 环境变量
    api_base: "https://api.openai.com/v1"
    timeout: 60
    max_retries: 3
    
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    api_base: "https://api.anthropic.com"
    timeout: 60
    
  google:
    api_key: "${GOOGLE_API_KEY}"
    
  azure:
    api_key: "${AZURE_API_KEY}"
    endpoint: "${AZURE_ENDPOINT}"
    api_version: "2024-02-01"

# 模型配置
models:
  # 对话模型
  gpt-4:
    provider: "openai"
    type: "chat"
    max_tokens: 4096
    supports_vision: true
    supports_functions: true
    cost_per_1k_tokens:
      input: 0.03
      output: 0.06
      
  claude-3-opus:
    provider: "anthropic"
    type: "chat"
    max_tokens: 4096
    supports_vision: true
    cost_per_1k_tokens:
      input: 0.015
      output: 0.075
      
  # 图像生成模型
  dall-e-3:
    provider: "openai"
    type: "image_generation"
    sizes: ["1024x1024", "1024x1792", "1792x1024"]
    cost_per_image:
      standard: 0.04
      hd: 0.08
      
  # 语音模型
  whisper-1:
    provider: "openai"
    type: "audio_transcription"
    cost_per_minute: 0.006
    
  tts-1-hd:
    provider: "openai"
    type: "text_to_speech"
    cost_per_1k_chars: 0.030

# 路由规则
routing:
  default_models:
    chat: "gpt-4"
    image_generation: "dall-e-3"
    audio_transcription: "whisper-1"
    text_to_speech: "tts-1-hd"
    embedding: "text-embedding-ada-002"
    
  # 任务路由规则
  rules:
    - condition:
        task_type: "code_generation"
        language: "python"
      preferred_model: "claude-3-opus"
      
    - condition:
        task_type: "translation"
        target_language: "zh"
      preferred_model: "gpt-4"

# 缓存配置
cache:
  enabled: true
  backend: "redis"  # memory|redis|disk
  ttl: 3600  # 秒
  max_size: "1GB"
  
  # 语义相似度阈值
  similarity_threshold: 0.95
  
  # 不缓存的方法
  exclude_methods: ["generate_image", "generate_speech"]

# 限流配置
rate_limits:
  # 全局限制
  global:
    requests_per_minute: 100
    requests_per_hour: 1000
    
  # 用户级别限制
  per_user:
    requests_per_minute: 20
    requests_per_hour: 200
    
  # 模型级别限制
  per_model:
    gpt-4:
      requests_per_minute: 10
      tokens_per_minute: 40000
      
    dall-e-3:
      requests_per_hour: 50

# 安全配置
security:
  # API密钥加密
  encryption:
    algorithm: "AES-256-GCM"
    key_file: "/secure/path/master.key"
    
  # 内容过滤
  content_filter:
    enabled: true
    block_patterns:
      - "(?i)password|secret|key"
      
  # 访问控制
  access_control:
    enabled: true
    whitelist_services:
      - "web-service"
      - "admin-service"
      
# 监控配置
monitoring:
  metrics:
    enabled: true
    export_interval: 60
    
  tracing:
    enabled: true
    sample_rate: 0.1
    
  # 成本追踪
  cost_tracking:
    enabled: true
    alert_threshold: 100  # 美元
    daily_limit: 1000     # 美元
```

### 4.2 模型能力映射配置 (model_capabilities.yaml)

```yaml
capabilities:
  text_generation:
    models:
      - gpt-4
      - gpt-3.5-turbo
      - claude-3-opus
      - claude-3-sonnet
      
  code_generation:
    models:
      - gpt-4
      - claude-3-opus
      - codellama-70b
      
  image_understanding:
    models:
      - gpt-4-vision-preview
      - claude-3-opus
      - gemini-pro-vision
      
  multilingual:
    models:
      - gpt-4
      - claude-3-opus
      - palm-2
```

## 5. 多模态支持设计

### 5.1 输入处理

```python
class MultiModalInput:
    """多模态输入处理器"""
    
    async def process_input(self, params: dict) -> dict:
        """处理多模态输入"""
        processed = {}
        
        # 文本处理
        if 'text' in params:
            processed['text'] = self._sanitize_text(params['text'])
            
        # 图像处理
        if 'images' in params:
            processed['images'] = []
            for image in params['images']:
                # 支持URL、base64、文件路径
                img_data = await self._load_image(image)
                # 格式转换、压缩、调整大小
                img_processed = await self._process_image(img_data)
                processed['images'].append(img_processed)
                
        # 音频处理
        if 'audio' in params:
            audio_data = await self._load_audio(params['audio'])
            # 格式转换、采样率调整
            processed['audio'] = await self._process_audio(audio_data)
            
        return processed
```

### 5.2 输出处理

```python
class MultiModalOutput:
    """多模态输出处理器"""
    
    async def format_output(self, 
                          raw_output: dict, 
                          output_format: str) -> dict:
        """格式化多模态输出"""
        formatted = {}
        
        # 文本输出
        if 'text' in raw_output:
            formatted['text'] = raw_output['text']
            
        # 图像输出
        if 'images' in raw_output:
            formatted['images'] = []
            for image in raw_output['images']:
                if output_format == 'url':
                    # 上传到对象存储，返回URL
                    url = await self._upload_image(image)
                    formatted['images'].append({'url': url})
                elif output_format == 'base64':
                    formatted['images'].append({'base64': image})
                    
        # 音频输出
        if 'audio' in raw_output:
            if output_format == 'url':
                url = await self._upload_audio(raw_output['audio'])
                formatted['audio'] = {'url': url}
            else:
                formatted['audio'] = {'base64': raw_output['audio']}
                
        return formatted
```

## 6. 安全设计

### 6.1 API密钥管理

```python
class SecureKeyManager:
    """安全的API密钥管理器"""
    
    def __init__(self, master_key_path: str):
        self.cipher = self._init_cipher(master_key_path)
        
    def encrypt_key(self, api_key: str) -> str:
        """加密API密钥"""
        return self.cipher.encrypt(api_key.encode()).decode()
        
    def decrypt_key(self, encrypted_key: str) -> str:
        """解密API密钥"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
        
    def rotate_keys(self):
        """定期轮换密钥"""
        # 实现密钥轮换逻辑
        pass
```

### 6.2 内容安全

```python
class ContentFilter:
    """内容安全过滤器"""
    
    async def check_content(self, content: dict) -> tuple[bool, str]:
        """检查内容安全性"""
        # 敏感词过滤
        if self._contains_sensitive_words(content):
            return False, "Contains sensitive content"
            
        # 恶意代码检测
        if self._contains_malicious_code(content):
            return False, "Contains potentially malicious code"
            
        # NSFW内容检测（图像）
        if 'images' in content:
            for image in content['images']:
                if await self._is_nsfw_image(image):
                    return False, "Contains inappropriate image"
                    
        return True, "Content is safe"
```

### 6.3 访问控制

```python
class AccessController:
    """访问控制器"""
    
    def __init__(self, config: dict):
        self.whitelist = set(config.get('whitelist_services', []))
        self.blacklist = set(config.get('blacklist_services', []))
        self.rate_limiter = RateLimiter(config.get('rate_limits', {}))
        
    async def check_access(self, 
                         service_name: str, 
                         user_id: str,
                         method: str) -> tuple[bool, str]:
        """检查访问权限"""
        # 黑白名单检查
        if service_name in self.blacklist:
            return False, "Service is blacklisted"
            
        if self.whitelist and service_name not in self.whitelist:
            return False, "Service not in whitelist"
            
        # 速率限制检查
        if not await self.rate_limiter.check_limit(user_id, method):
            return False, "Rate limit exceeded"
            
        return True, "Access granted"
```

## 7. 性能优化

### 7.1 连接池管理

```python
class ConnectionPoolManager:
    """连接池管理器"""
    
    def __init__(self):
        self.pools = {}
        
    async def get_session(self, provider: str) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if provider not in self.pools:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300
            )
            self.pools[provider] = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self.pools[provider]
```

### 7.2 请求批处理

```python
class BatchProcessor:
    """批处理器"""
    
    def __init__(self, batch_size: int = 10, wait_time: float = 0.1):
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.pending_requests = []
        
    async def add_request(self, request: dict) -> asyncio.Future:
        """添加请求到批处理队列"""
        future = asyncio.Future()
        self.pending_requests.append((request, future))
        
        if len(self.pending_requests) >= self.batch_size:
            await self._process_batch()
        else:
            asyncio.create_task(self._wait_and_process())
            
        return future
        
    async def _process_batch(self):
        """处理一批请求"""
        batch = self.pending_requests[:self.batch_size]
        self.pending_requests = self.pending_requests[self.batch_size:]
        
        # 批量调用API
        results = await self._batch_api_call(batch)
        
        # 分发结果
        for (request, future), result in zip(batch, results):
            future.set_result(result)
```

### 7.3 预测性缓存

```python
class PredictiveCache:
    """预测性缓存"""
    
    async def prefetch(self, context: dict):
        """基于上下文预取可能的请求"""
        # 分析用户行为模式
        patterns = await self._analyze_patterns(context['user_id'])
        
        # 预测下一个可能的请求
        predictions = self._predict_next_requests(patterns, context)
        
        # 预先缓存结果
        for prediction in predictions[:5]:  # 只预取前5个
            asyncio.create_task(self._prefetch_result(prediction))
```

## 8. 错误处理

### 8.1 重试策略

```python
class RetryStrategy:
    """智能重试策略"""
    
    def __init__(self):
        self.strategies = {
            'rate_limit': self._handle_rate_limit,
            'timeout': self._handle_timeout,
            'server_error': self._handle_server_error,
            'api_error': self._handle_api_error
        }
        
    async def execute_with_retry(self, 
                               func: callable, 
                               max_retries: int = 3) -> any:
        """带重试的执行"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)
                
                if error_type in self.strategies:
                    should_retry, wait_time = await self.strategies[error_type](
                        e, attempt
                    )
                    if should_retry:
                        await asyncio.sleep(wait_time)
                        continue
                        
                raise e
                
        raise last_error
```

### 8.2 降级策略

```python
class FallbackStrategy:
    """降级策略"""
    
    def __init__(self, model_hierarchy: dict):
        self.model_hierarchy = model_hierarchy
        
    async def execute_with_fallback(self, 
                                  task: dict, 
                                  preferred_model: str) -> dict:
        """带降级的执行"""
        models = self._get_fallback_chain(task['type'], preferred_model)
        
        for model in models:
            try:
                # 尝试使用当前模型
                result = await self._execute_task(task, model)
                result['used_model'] = model
                result['fallback_level'] = models.index(model)
                return result
            except ModelUnavailableError:
                continue
                
        raise AllModelsFailedError("All models in fallback chain failed")
```

## 9. 监控与可观测性

### 9.1 指标收集

```python
class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics = {
            'request_count': Counter('ai_service_requests_total'),
            'request_duration': Histogram('ai_service_request_duration_seconds'),
            'token_usage': Counter('ai_service_tokens_total'),
            'cost': Counter('ai_service_cost_dollars'),
            'cache_hit_rate': Gauge('ai_service_cache_hit_rate'),
            'active_requests': Gauge('ai_service_active_requests')
        }
        
    def record_request(self, method: str, model: str, duration: float):
        """记录请求指标"""
        self.metrics['request_count'].labels(
            method=method, 
            model=model
        ).inc()
        
        self.metrics['request_duration'].labels(
            method=method,
            model=model
        ).observe(duration)
```

### 9.2 日志记录

```python
class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, service_name: str):
        self.logger = self._setup_logger(service_name)
        
    def log_request(self, request_id: str, context: dict):
        """记录请求日志"""
        self.logger.info(
            "AI request received",
            extra={
                'request_id': request_id,
                'method': context['method'],
                'model': context.get('model'),
                'user_id': context.get('user_id'),
                'service': context.get('service_name')
            }
        )
        
    def log_response(self, request_id: str, response: dict, duration: float):
        """记录响应日志"""
        self.logger.info(
            "AI request completed",
            extra={
                'request_id': request_id,
                'status': response['status'],
                'duration_ms': duration * 1000,
                'tokens_used': response.get('usage', {}).get('total_tokens'),
                'cost': response.get('usage', {}).get('total_cost')
            }
        )
```

## 10. 扩展性设计

### 10.1 插件系统

```python
class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins = {}
        
    def register_plugin(self, plugin_type: str, plugin: Plugin):
        """注册插件"""
        if plugin_type not in self.plugins:
            self.plugins[plugin_type] = []
        self.plugins[plugin_type].append(plugin)
        
    async def execute_plugins(self, 
                            plugin_type: str, 
                            event: str, 
                            data: dict) -> dict:
        """执行插件"""
        if plugin_type not in self.plugins:
            return data
            
        for plugin in self.plugins[plugin_type]:
            if hasattr(plugin, event):
                data = await getattr(plugin, event)(data)
                
        return data

# 插件示例
class CustomModelPlugin(Plugin):
    """自定义模型插件"""
    
    async def before_request(self, data: dict) -> dict:
        """请求前处理"""
        # 添加自定义头
        data['headers']['X-Custom-Header'] = 'value'
        return data
        
    async def after_response(self, data: dict) -> dict:
        """响应后处理"""
        # 添加自定义字段
        data['custom_field'] = 'custom_value'
        return data
```

### 10.2 模型适配器接口

```python
from abc import ABC, abstractmethod

class ModelAdapter(ABC):
    """模型适配器基类"""
    
    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> dict:
        """对话接口"""
        pass
        
    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> dict:
        """图像生成接口"""
        pass
        
    @abstractmethod
    async def transcribe_audio(self, audio: bytes, **kwargs) -> dict:
        """语音识别接口"""
        pass
        
    @abstractmethod
    def supports_streaming(self) -> bool:
        """是否支持流式响应"""
        pass
        
    @abstractmethod
    def get_model_info(self) -> dict:
        """获取模型信息"""
        pass

# 新模型适配器示例
class CustomModelAdapter(ModelAdapter):
    """自定义模型适配器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = CustomAPIClient(config['api_key'])
        
    async def chat(self, messages: list, **kwargs) -> dict:
        # 实现自定义模型的对话逻辑
        response = await self.client.create_chat_completion(
            messages=messages,
            **kwargs
        )
        return self._format_response(response)
```

## 11. 部署方案

### 11.1 容器化部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV AI_SERVICE_CONFIG=/app/config/ai_service_config.yaml

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:9999/health')"

# 启动服务
CMD ["python", "ai_service.py"]
```

### 11.2 资源需求

```yaml
# Kubernetes资源配置示例
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
    
# 自动扩缩容配置
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## 12. 开发路线图

### Phase 1: 核心功能与IPC集成（2周）
- [ ] 基于examples-ipc/python/service.py创建AI服务框架
- [ ] 实现完整的IPC协议（消息编解码、服务注册、心跳）
- [ ] 测试与Neo Framework的基础通信
- [ ] 实现OpenAI适配器
- [ ] 实现基本的chat方法（非流式）
- [ ] 配置系统基础实现

### Phase 2: 多模型支持（2周）
- [ ] Anthropic适配器
- [ ] Google/Gemini适配器
- [ ] 国内模型适配器（百度、阿里等）
- [ ] 智能路由实现
- [ ] 模型能力映射

### Phase 3: 高级特性（2周）
- [ ] 流式响应支持
- [ ] 多模态输入输出
- [ ] 语音识别与合成
- [ ] 向量嵌入支持
- [ ] 批处理优化

### Phase 4: 企业特性（2周）
- [ ] 高级缓存系统
- [ ] 细粒度限流
- [ ] 成本控制与预算
- [ ] 安全增强
- [ ] 审计日志

### Phase 5: 可观测性（1周）
- [ ] Prometheus指标
- [ ] 分布式追踪
- [ ] 日志聚合
- [ ] 告警系统
- [ ] 仪表板

### Phase 6: 生产就绪（1周）
- [ ] 性能调优
- [ ] 压力测试
- [ ] 文档完善
- [ ] 部署脚本
- [ ] 运维手册

## 13. 使用示例

### 13.1 基础对话

```python
# Python客户端示例
import asyncio
from neo_client import NeoIPCClient

async def chat_example():
    client = NeoIPCClient("localhost", 9999)
    await client.connect()
    
    response = await client.call("ai-service", "chat", {
        "messages": [
            {"role": "user", "content": "解释一下量子计算"}
        ],
        "model": "gpt-4",
        "temperature": 0.7
    })
    
    print(f"AI回复: {response['data']['content']}")
    print(f"使用的模型: {response['data']['model']}")
    print(f"消耗的token: {response['data']['usage']['total_tokens']}")
    print(f"成本: ${response['data']['usage']['total_cost']}")

asyncio.run(chat_example())
```

### 13.2 多模态对话

```python
async def multimodal_example():
    client = NeoIPCClient("localhost", 9999)
    await client.connect()
    
    # 读取图片
    with open("chart.png", "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = await client.call("ai-service", "chat", {
        "messages": [
            {
                "role": "user",
                "content": "分析这个图表中的数据趋势",
                "images": [image_data]
            }
        ],
        "model": "gpt-4-vision-preview"
    })
    
    print(f"分析结果: {response['data']['content']}")
```

### 13.3 流式响应

```python
async def stream_example():
    client = NeoIPCClient("localhost", 9999)
    await client.connect()
    
    # 注册流式处理器
    async def handle_stream(chunk):
        if chunk['status'] == 'streaming':
            print(chunk['data']['delta'], end='', flush=True)
        elif chunk['status'] == 'stream_end':
            print(f"\n\n总token数: {chunk['data']['usage']['total_tokens']}")
    
    await client.call_stream("ai-service", "chat", {
        "messages": [
            {"role": "user", "content": "写一个关于AI的短故事"}
        ],
        "model": "gpt-4",
        "stream": True
    }, handle_stream)
```

## 14. 总结

Neo AI Service 通过统一的接口和智能的路由系统，为Neo Framework提供了强大而灵活的AI能力。其主要优势包括：

1. **统一接口**: 屏蔽不同AI提供商的差异
2. **配置驱动**: 通过配置即可接入新模型
3. **多模态支持**: 完整的文本、图像、音频处理能力
4. **企业级特性**: 缓存、限流、成本控制、安全防护
5. **高可扩展性**: 插件系统和适配器模式便于扩展
6. **生产就绪**: 完善的监控、日志和错误处理

通过这个服务，Neo Framework的用户可以轻松地在应用中集成最先进的AI能力，而无需关心底层的复杂性。