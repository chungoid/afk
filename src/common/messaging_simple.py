import asyncio
import os
import json
import logging
import signal
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Coroutine, Optional, List

logger = logging.getLogger("messaging")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def exponential_backoff(attempt: int, base: float = 0.1, factor: float = 2.0, max_delay: float = 10.0) -> float:
    """Calculate exponential backoff delay."""
    delay = base * (factor ** attempt)
    return min(delay, max_delay)

class MessagingClient(ABC):
    """
    Abstract base messaging client.
    """

    @abstractmethod
    async def start(self):
        """
        Initialize connections/resources.
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Close connections/resources.
        """
        pass

    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]):
        """
        Publish a JSON-serializable message to a topic.
        """
        pass

    @abstractmethod
    def subscribe(self,
                  topic: str,
                  callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
                  group_id: Optional[str] = None):
        """
        Subscribe to a topic and register callback for incoming messages.
        """
        pass

class SimpleMessagingClient(MessagingClient):
    """
    Simple in-memory messaging client for development/testing
    """
    
    def __init__(self):
        self.topics: Dict[str, List[Callable]] = {}
        self.is_running = False
        
    async def start(self):
        self.is_running = True
        logger.info("Simple messaging client started")
        
    async def stop(self):
        self.is_running = False
        logger.info("Simple messaging client stopped")
        
    async def publish(self, topic: str, message: Dict[str, Any]):
        if not self.is_running:
            return
            
        logger.debug(f"Publishing to {topic}: {message}")
        
        # Simulate async processing
        if topic in self.topics:
            for callback in self.topics[topic]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error in callback for topic {topic}: {e}")
                    
    def subscribe(self,
                  topic: str,
                  callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
                  group_id: Optional[str] = None):
        if topic not in self.topics:
            self.topics[topic] = []
        self.topics[topic].append(callback)
        logger.info(f"Subscribed to topic {topic} with group {group_id}")

def create_messaging_client(loop: Optional[asyncio.AbstractEventLoop] = None) -> MessagingClient:
    """
    Factory to create the appropriate messaging client.
    For now, using simple in-memory client due to dependency issues.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
        
    # Use simple client for now
    return SimpleMessagingClient()

def setup_signal_handlers(loop: asyncio.AbstractEventLoop, client: MessagingClient):
    """
    Register signal handlers for graceful shutdown.
    """
    signals = (signal.SIGINT, signal.SIGTERM)

    for s in signals:
        loop.add_signal_handler(
            s,
            lambda s=s: asyncio.create_task(_shutdown(loop, client, s))
        )

async def _shutdown(loop: asyncio.AbstractEventLoop, client: MessagingClient, sig):
    logger.info("Received exit signal %s, shutting down...", sig.name)
    await client.stop()
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop() 