"""Neo Framework IPC Protocol Implementation"""

import struct
import json
from enum import IntEnum
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union


class MessageType(IntEnum):
    """IPC message types - must match Go framework definitions"""
    REQUEST = 1     # 0x01
    RESPONSE = 2    # 0x02
    REGISTER = 3    # 0x03
    HEARTBEAT = 4   # 0x04
    ERROR = 5       # 0x05


@dataclass
class Message:
    """IPC message structure"""
    msg_type: MessageType
    id: str
    service: str
    method: str
    data: Union[bytes, dict, str]
    metadata: Dict[str, str]


def encode_message(msg: Message) -> bytes:
    """Encode a message to binary format"""
    # Convert data to bytes
    if isinstance(msg.data, dict):
        data_bytes = json.dumps(msg.data).encode('utf-8')
    elif isinstance(msg.data, str):
        data_bytes = msg.data.encode('utf-8')
    elif isinstance(msg.data, bytes):
        data_bytes = msg.data
    else:
        data_bytes = str(msg.data).encode('utf-8')
    
    # Encode strings
    id_bytes = msg.id.encode('utf-8')
    service_bytes = msg.service.encode('utf-8')
    method_bytes = msg.method.encode('utf-8')
    metadata_json = json.dumps(msg.metadata).encode('utf-8')
    
    # Build message content
    content = bytearray()
    
    # Message type (1 byte)
    content.extend(struct.pack('<B', msg.msg_type))
    
    # ID
    content.extend(struct.pack('<I', len(id_bytes)))
    content.extend(id_bytes)
    
    # Service
    content.extend(struct.pack('<I', len(service_bytes)))
    content.extend(service_bytes)
    
    # Method
    content.extend(struct.pack('<I', len(method_bytes)))
    content.extend(method_bytes)
    
    # Metadata
    content.extend(struct.pack('<I', len(metadata_json)))
    content.extend(metadata_json)
    
    # Data
    content.extend(struct.pack('<I', len(data_bytes)))
    content.extend(data_bytes)
    
    # Add message length header
    return struct.pack('<I', len(content)) + bytes(content)


def decode_message(data: bytes) -> Message:
    """Decode a binary message"""
    offset = 0
    
    # Read message type
    msg_type = MessageType(data[offset])
    offset += 1
    
    # Read ID
    id_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    msg_id = data[offset:offset+id_len].decode('utf-8')
    offset += id_len
    
    # Read service
    service_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    service = data[offset:offset+service_len].decode('utf-8')
    offset += service_len
    
    # Read method
    method_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    method = data[offset:offset+method_len].decode('utf-8')
    offset += method_len
    
    # Read metadata
    metadata_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    metadata_json = data[offset:offset+metadata_len].decode('utf-8')
    metadata = json.loads(metadata_json) if metadata_json else {}
    offset += metadata_len
    
    # Read data
    data_len = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    data_bytes = data[offset:offset+data_len]
    
    # Try to parse as JSON
    try:
        data_obj = json.loads(data_bytes.decode('utf-8'))
    except:
        data_obj = data_bytes
    
    return Message(
        msg_type=msg_type,
        id=msg_id,
        service=service,
        method=method,
        data=data_obj,
        metadata=metadata
    )