# Neo Framework IPC 通信协议文档

## 概述

Neo Framework 使用基于TCP Socket的二进制协议进行进程间通信（IPC）。该协议设计简洁高效，支持多语言客户端实现。

## 连接信息

- **默认端口**: 9999
- **协议类型**: TCP
- **编码格式**: 二进制
- **字节序**: 小端序（Little Endian）

## 消息格式

### 基础消息结构

每个消息由消息头和消息体组成：

```
[消息长度:4字节][消息内容:N字节]
```

- **消息长度**: 32位无符号整数，小端序，表示消息内容的字节数
- **消息内容**: 实际的消息数据

### 消息内容格式

消息内容按以下顺序编码：

```
[类型:1字节][ID长度:4字节][ID:N字节][服务名长度:4字节][服务名:N字节]
[方法名长度:4字节][方法名:N字节][元数据长度:4字节][元数据JSON:N字节]
[数据长度:4字节][数据:N字节]
```

字段说明：
- **类型** (1字节): 消息类型，见下方消息类型定义
- **ID长度** (4字节): 消息ID的字节长度
- **ID** (变长): 消息ID字符串（UTF-8编码）
- **服务名长度** (4字节): 服务名的字节长度
- **服务名** (变长): 服务名字符串（UTF-8编码）
- **方法名长度** (4字节): 方法名的字节长度
- **方法名** (变长): 方法名字符串（UTF-8编码）
- **元数据长度** (4字节): 元数据JSON的字节长度
- **元数据JSON** (变长): JSON格式的元数据（UTF-8编码）
- **数据长度** (4字节): 数据的字节长度
- **数据** (变长): 实际数据内容

## 消息类型

```python
# 消息类型定义
REGISTER = 0x01    # 服务注册
REQUEST = 0x02     # 请求
RESPONSE = 0x03    # 响应
ERROR = 0x04       # 错误
HEARTBEAT = 0x05   # 心跳
```

## 通信流程

### 1. 服务注册

客户端连接后必须先注册服务：

```python
# 注册消息示例
{
    "type": REGISTER,
    "id": "",
    "service": "ai-service",
    "method": "",
    "metadata": {},
    "data": {
        "name": "ai-service",
        "metadata": {
            "version": "1.0.0",
            "protocol": "ipc",
            "language": "python",
            "capabilities": ["chat", "generate_image"]
        }
    }
}
```

### 2. 接收请求

注册成功后，服务将接收来自框架的请求：

```python
# 请求消息示例
{
    "type": REQUEST,
    "id": "req-123456",
    "service": "ai-service",
    "method": "chat",
    "metadata": {
        "user_id": "user-001",
        "trace_id": "trace-789"
    },
    "data": {
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "model": "gpt-3.5-turbo"
    }
}
```

### 3. 发送响应

服务处理完请求后发送响应：

```python
# 响应消息示例
{
    "type": RESPONSE,
    "id": "req-123456",  # 必须与请求ID相同
    "service": "ai-service",
    "method": "chat",
    "metadata": {},
    "data": {
        "status": "success",
        "data": {
            "content": "Hello! How can I help you?",
            "model": "gpt-3.5-turbo",
            "usage": {
                "total_tokens": 25
            }
        }
    }
}
```

### 4. 错误处理

发生错误时返回错误消息：

```python
# 错误消息示例
{
    "type": ERROR,
    "id": "req-123456",
    "service": "ai-service",
    "method": "chat",
    "metadata": {"error": "true"},
    "data": {
        "error": "Model not available",
        "code": "MODEL_UNAVAILABLE"
    }
}
```

### 5. 心跳维持

服务需要定期发送心跳保持连接：

```python
# 心跳消息示例
{
    "type": HEARTBEAT,
    "id": "",
    "service": "ai-service",
    "method": "",
    "metadata": {},
    "data": b""
}
```

建议心跳间隔：30秒

## Python 实现示例

### 消息编码

```python
import struct
import json

def encode_message(msg_type, id, service, method, metadata, data):
    """编码消息为二进制格式"""
    # 编码各个字段
    id_bytes = id.encode('utf-8')
    service_bytes = service.encode('utf-8')
    method_bytes = method.encode('utf-8')
    metadata_json = json.dumps(metadata).encode('utf-8')
    
    # 如果data是字典，转换为JSON
    if isinstance(data, dict):
        data_bytes = json.dumps(data).encode('utf-8')
    else:
        data_bytes = data if isinstance(data, bytes) else str(data).encode('utf-8')
    
    # 构建消息内容
    content = struct.pack('<B', msg_type)  # 消息类型
    content += struct.pack('<I', len(id_bytes)) + id_bytes
    content += struct.pack('<I', len(service_bytes)) + service_bytes
    content += struct.pack('<I', len(method_bytes)) + method_bytes
    content += struct.pack('<I', len(metadata_json)) + metadata_json
    content += struct.pack('<I', len(data_bytes)) + data_bytes
    
    # 添加消息长度头
    message = struct.pack('<I', len(content)) + content
    
    return message
```

### 消息解码

```python
def decode_message(data):
    """解码二进制消息"""
    offset = 0
    
    # 读取消息类型
    msg_type = struct.unpack('<B', data[offset:offset+1])[0]
    offset += 1
    
    # 读取ID
    id_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    id = data[offset:offset+id_len].decode('utf-8')
    offset += id_len
    
    # 读取服务名
    service_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    service = data[offset:offset+service_len].decode('utf-8')
    offset += service_len
    
    # 读取方法名
    method_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    method = data[offset:offset+method_len].decode('utf-8')
    offset += method_len
    
    # 读取元数据
    metadata_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    metadata = json.loads(data[offset:offset+metadata_len].decode('utf-8'))
    offset += metadata_len
    
    # 读取数据
    data_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    data_bytes = data[offset:offset+data_len]
    
    # 尝试解析为JSON
    try:
        data_obj = json.loads(data_bytes.decode('utf-8'))
    except:
        data_obj = data_bytes
    
    return {
        'type': msg_type,
        'id': id,
        'service': service,
        'method': method,
        'metadata': metadata,
        'data': data_obj
    }
```

### 完整客户端示例

```python
import asyncio
import struct
import json

class NeoIPCClient:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        
    async def connect(self):
        """连接到Neo Framework"""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )
        print(f"Connected to Neo Framework at {self.host}:{self.port}")
        
    async def register_service(self, service_name, metadata=None):
        """注册服务"""
        register_data = {
            "name": service_name,
            "metadata": metadata or {}
        }
        
        msg = encode_message(
            msg_type=0x01,  # REGISTER
            id="",
            service=service_name,
            method="",
            metadata={},
            data=register_data
        )
        
        self.writer.write(msg)
        await self.writer.drain()
        print(f"Service '{service_name}' registered")
        
    async def send_response(self, request_id, method, result):
        """发送响应"""
        msg = encode_message(
            msg_type=0x03,  # RESPONSE
            id=request_id,
            service=self.service_name,
            method=method,
            metadata={},
            data=result
        )
        
        self.writer.write(msg)
        await self.writer.drain()
        
    async def handle_requests(self):
        """处理请求循环"""
        while True:
            # 读取消息长度
            length_data = await self.reader.readexactly(4)
            msg_len = struct.unpack('<I', length_data)[0]
            
            # 读取消息内容
            msg_data = await self.reader.readexactly(msg_len)
            message = decode_message(msg_data)
            
            if message['type'] == 0x02:  # REQUEST
                # 处理请求
                result = await self.handle_request(message)
                # 发送响应
                await self.send_response(
                    message['id'],
                    message['method'],
                    result
                )
```

## 流式响应支持

对于需要流式返回数据的场景（如AI生成），可以发送多个响应消息：

```python
# 流式响应示例
async def handle_streaming_request(request):
    request_id = request['id']
    
    # 发送流式数据块
    for chunk in generate_stream():
        await send_response(request_id, {
            "status": "streaming",
            "data": {"delta": chunk}
        }, metadata={"streaming": "true"})
    
    # 发送结束标记
    await send_response(request_id, {
        "status": "stream_end",
        "data": {"total": total_data}
    }, metadata={"streaming": "true", "final": "true"})
```

## 最佳实践

### 1. 连接管理
- 实现自动重连机制
- 正确处理连接断开
- 使用心跳保持连接活跃

### 2. 错误处理
- 捕获所有异常并返回错误响应
- 提供有意义的错误信息
- 记录详细的错误日志

### 3. 性能优化
- 使用连接池复用连接
- 批量处理请求
- 实现请求超时机制

### 4. 安全考虑
- 验证请求数据的合法性
- 限制消息大小防止内存溢出
- 实现访问控制和认证机制

## 调试技巧

### 1. 消息日志

```python
def log_message(direction, message):
    """记录消息日志"""
    print(f"{direction} Message:")
    print(f"  Type: {message['type']}")
    print(f"  ID: {message['id']}")
    print(f"  Service: {message['service']}")
    print(f"  Method: {message['method']}")
    print(f"  Data: {message['data']}")
```

### 2. 协议分析

使用Wireshark或tcpdump捕获网络包分析协议：

```bash
# 捕获端口9999的TCP流量
tcpdump -i lo -w neo-ipc.pcap port 9999
```

### 3. 测试工具

创建简单的测试客户端验证服务：

```python
async def test_service():
    client = NeoIPCClient()
    await client.connect()
    
    # 测试请求
    response = await client.call('ai-service', 'chat', {
        'messages': [{'role': 'user', 'content': 'test'}]
    })
    
    print(f"Response: {response}")
```

## 多语言实现参考

- **Go**: 参考 `core/protocol/binary.go`
- **Python**: 参考 `examples-ipc/python/service.py`
- **Node.js**: 参考 `examples-ipc/nodejs/service.js`
- **Java**: 参考 `examples-ipc/java/Service.java`
- **PHP**: 参考 `examples-ipc/php/service.php`

## 常见问题

### Q: 如何处理大消息？
A: 协议支持最大4GB的消息，但建议将大数据分块传输或使用流式响应。

### Q: 心跳失败会怎样？
A: 连续3次心跳失败后，框架会断开连接。服务需要重新连接和注册。

### Q: 可以同时处理多个请求吗？
A: 是的，使用异步编程模型可以并发处理多个请求。

### Q: 如何实现请求超时？
A: 在客户端设置超时计时器，超时后发送取消请求或忽略响应。