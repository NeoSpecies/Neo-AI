"""IPC communication module for Neo AI Service"""

from .client import NeoIPCClient
from .protocol import Message, MessageType

__all__ = ['NeoIPCClient', 'Message', 'MessageType']