"""Neo IPC Client implementation for AI Service"""

import asyncio
import struct
import logging
from typing import Dict, Any, Optional, Callable
from .protocol import Message, MessageType, encode_message, decode_message

logger = logging.getLogger(__name__)


class NeoIPCClient:
    """IPC client for communicating with Neo Framework"""
    
    def __init__(self, host: str = "localhost", port: int = 9999):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.handlers: Dict[str, Callable] = {}
        self.service_name: Optional[str] = None
        self.connected = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> None:
        """Connect to Neo Framework IPC server"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.connected = True
            logger.info(f"Connected to Neo Framework at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo Framework: {e}")
            raise
            
    async def disconnect(self) -> None:
        """Disconnect from Neo Framework"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            
        self.connected = False
        logger.info("Disconnected from Neo Framework")
        
    async def register_service(self, service_name: str, metadata: Dict[str, Any] = None) -> None:
        """Register service with Neo Framework"""
        if not self.connected:
            raise RuntimeError("Not connected to Neo Framework")
            
        self.service_name = service_name
        metadata = metadata or {}
        
        register_data = {
            "name": service_name,
            "metadata": metadata
        }
        
        msg = Message(
            msg_type=MessageType.REGISTER,
            id="",
            service=service_name,
            method="",
            data=register_data,
            metadata={}
        )
        
        await self._send_message(msg)
        logger.info(f"Service '{service_name}' registered successfully")
        
        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
    def add_handler(self, method: str, handler: Callable) -> None:
        """Add a method handler"""
        self.handlers[method] = handler
        logger.info(f"Handler registered for method: {method}")
        
    def handler(self, method: str):
        """Decorator for registering method handlers"""
        def decorator(func):
            self.add_handler(method, func)
            return func
        return decorator
        
    async def _send_message(self, msg: Message) -> None:
        """Send a message to Neo Framework"""
        if not self.writer:
            raise RuntimeError("Not connected to Neo Framework")
            
        try:
            data = encode_message(msg)
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
            
    async def _read_message(self) -> Optional[Message]:
        """Read a message from Neo Framework"""
        if not self.reader:
            return None
            
        try:
            # Read message length
            len_bytes = await self.reader.readexactly(4)
            msg_len = struct.unpack('<I', len_bytes)[0]
            
            # Read message content
            msg_bytes = await self.reader.readexactly(msg_len)
            
            return decode_message(msg_bytes)
        except asyncio.IncompleteReadError:
            logger.warning("Connection closed by Neo Framework")
            return None
        except Exception as e:
            logger.error(f"Failed to read message: {e}")
            raise
            
    async def _handle_request(self, msg: Message) -> None:
        """Handle an incoming request"""
        if msg.method not in self.handlers:
            error_msg = Message(
                msg_type=MessageType.ERROR,
                id=msg.id,
                service=self.service_name,
                method=msg.method,
                data={"error": f"Method '{msg.method}' not found"},
                metadata={"error": "true"}
            )
            await self._send_message(error_msg)
            return
            
        try:
            # Get handler
            handler = self.handlers[msg.method]
            
            # Extract request data
            request_data = msg.data if isinstance(msg.data, dict) else {}
            
            # Call handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(request_data, msg.metadata)
            else:
                result = handler(request_data, msg.metadata)
                
            # Send response
            response = Message(
                msg_type=MessageType.RESPONSE,
                id=msg.id,
                service=self.service_name,
                method=msg.method,
                data=result,
                metadata={}
            )
            await self._send_message(response)
            
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            error_msg = Message(
                msg_type=MessageType.ERROR,
                id=msg.id,
                service=self.service_name,
                method=msg.method,
                data={"error": str(e), "type": type(e).__name__},
                metadata={"error": "true"}
            )
            await self._send_message(error_msg)
            
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to Neo Framework"""
        while self.connected:
            try:
                await asyncio.sleep(30)
                
                heartbeat = Message(
                    msg_type=MessageType.HEARTBEAT,
                    id="",
                    service=self.service_name,
                    method="",
                    data=b"",
                    metadata={}
                )
                await self._send_message(heartbeat)
                logger.debug("Heartbeat sent")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
                
    async def run(self) -> None:
        """Run the service and handle incoming requests"""
        if not self.connected:
            raise RuntimeError("Not connected to Neo Framework")
            
        if not self.service_name:
            raise RuntimeError("Service not registered")
            
        logger.info(f"Service '{self.service_name}' is running...")
        
        while self.connected:
            try:
                msg = await self._read_message()
                if msg is None:
                    break
                    
                if msg.msg_type == MessageType.REQUEST:
                    # Handle request in a separate task to avoid blocking
                    asyncio.create_task(self._handle_request(msg))
                    
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                break
                
        logger.info("Service stopped")
        
    async def send_streaming_response(self, request_id: str, method: str, 
                                    chunk: Any, is_final: bool = False) -> None:
        """Send a streaming response chunk"""
        metadata = {"streaming": "true"}
        if is_final:
            metadata["final"] = "true"
            
        response = Message(
            msg_type=MessageType.RESPONSE,
            id=request_id,
            service=self.service_name,
            method=method,
            data=chunk,
            metadata=metadata
        )
        await self._send_message(response)