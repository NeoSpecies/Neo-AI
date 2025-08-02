# Neo AI Service Starter Pack 结构说明

## 文件结构

```
neo-ai-service-starter/
├── neo-framework.exe          # Neo Framework 可执行文件
├── start-neo.bat             # Windows启动脚本
├── README.md                 # AI服务开发完整指南
├── IPC_PROTOCOL.md           # IPC通信协议详细文档
├── AI_SERVICE_DESIGN.md      # AI服务详细设计文档
├── STRUCTURE.md              # 本文件 - 结构说明
└── ipc-examples/             # IPC示例代码
    └── python/
        ├── service.py        # Python IPC客户端示例
        └── README.md         # Python示例说明
```

## 快速开始

1. **启动 Neo Framework**
   ```bash
   # Windows
   start-neo.bat
   
   # 或直接运行
   neo-framework.exe -port 9999
   ```

2. **查看开发指南**
   - 打开 `README.md` 了解完整的开发流程
   - 查看 `IPC_PROTOCOL.md` 了解通信协议细节
   - 参考 `AI_SERVICE_DESIGN.md` 了解设计理念

3. **开始开发**
   ```bash
   # 创建新项目
   mkdir my-ai-service
   cd my-ai-service
   
   # 参考 ipc-examples/python/service.py 开始开发
   ```

## 重要文件说明

### neo-framework.exe
- Neo Framework 的核心服务器
- 默认监听 9999 端口
- 支持多语言客户端连接

### README.md
- 完整的 AI 服务开发指南
- 包含技术选型、架构设计、开发步骤
- 提供代码示例和最佳实践

### IPC_PROTOCOL.md
- 详细的二进制协议说明
- 消息格式定义
- 多语言实现示例

### AI_SERVICE_DESIGN.md
- AI 服务的完整设计文档
- 包含所有接口定义
- 配置系统说明
- 部署和监控方案

### ipc-examples/python/service.py
- 可直接运行的 Python IPC 客户端示例
- 展示了完整的通信流程
- 可作为开发基础

## 下一步

1. 阅读 `README.md` 了解整体方案
2. 运行 `start-neo.bat` 启动框架
3. 基于 `ipc-examples/python/service.py` 开始开发
4. 参考 `IPC_PROTOCOL.md` 处理通信细节
5. 遵循 `AI_SERVICE_DESIGN.md` 的设计规范

## 注意事项

- 确保 Python 3.9+ 已安装
- 安装必要的依赖包（参见 README.md）
- API 密钥需要通过环境变量配置
- 本地模型（vLLM/Ollama）需要额外安装

祝开发顺利！