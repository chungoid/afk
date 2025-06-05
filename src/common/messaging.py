import asyncio
import os
import json
import logging
import signal
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Coroutine, Optional, List

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer, ConsumerRecord
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaProducer = None
    AIOKafkaConsumer = None
    ConsumerRecord = None

try:
    import aio_pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False
    aio_pika = None

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

logger = logging.getLogger("messaging")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

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

def exponential_backoff(attempt: int, base: float = 0.1, factor: float = 2.0, max_delay: float = 10.0) -> float:
    delay = min(base * (factor ** attempt), max_delay)
    return delay

class KafkaMessagingClient(MessagingClient):
    """
    Kafka-based messaging using aiokafka.
    """

    def __init__(self,
                 brokers: List[str],
                 loop: asyncio.AbstractEventLoop,
                 client_id: str = "messaging-client"):
        self.brokers = brokers
        self.loop = loop
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumers: List[AIOKafkaConsumer] = []
        self.tasks: List[asyncio.Task] = []
        self.client_id = client_id
        self._stopped = asyncio.Event()

    async def start(self):
        if not KAFKA_AVAILABLE:
            raise RuntimeError("aiokafka not available")
        self.producer = AIOKafkaProducer(
            loop=self.loop,
            bootstrap_servers=self.brokers,
            client_id=self.client_id,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        self._stopped.set()
        for c in self.consumers:
            await c.stop()
        for t in self.tasks:
            t.cancel()
        if self.producer:
            await self.producer.stop()
        logger.info("Kafka messaging stopped")

    async def publish(self, topic: str, message: Dict[str, Any]):
        if not self.producer:
            raise RuntimeError("Producer not started")
        attempt = 0
        while True:
            try:
                await self.producer.send_and_wait(topic, message)
                logger.debug("Published to %s: %s", topic, message)
                return
            except Exception as e:
                delay = exponential_backoff(attempt)
                logger.warning("Publish failed, attempt %d, retrying in %.2f: %s", attempt, delay, e)
                await asyncio.sleep(delay)
                attempt += 1

    def subscribe(self,
                  topic: str,
                  callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
                  group_id: Optional[str] = None):
        if group_id is None:
            group_id = f"{self.client_id}-{topic}"
        consumer = AIOKafkaConsumer(
            topic,
            loop=self.loop,
            bootstrap_servers=self.brokers,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset="earliest",
            enable_auto_commit=True
        )
        self.consumers.append(consumer)

        async def _consume():
            await consumer.start()
            logger.info("Kafka consumer started for topic=%s, group=%s", topic, group_id)
            try:
                async for msg in consumer:
                    await self._handle_record(msg, callback)
                    if self._stopped.is_set():
                        break
            except asyncio.CancelledError:
                pass
            finally:
                await consumer.stop()
                logger.info("Kafka consumer stopped for topic=%s", topic)

        task = self.loop.create_task(_consume())
        self.tasks.append(task)

    async def _handle_record(self, record: ConsumerRecord, callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]):
        try:
            payload = record.value
            logger.debug("Received record on %s: %s", record.topic, payload)
            await callback(payload)
        except Exception as e:
            logger.exception("Error handling record: %s", e)
            # Let orchestrator handle retries/failures

class RedisStreamMessagingClient(MessagingClient):
    """
    Redis Streams-based messaging using aioredis.
    """

    def __init__(self,
                 url: str,
                 group: str,
                 consumer_name: str,
                 loop: asyncio.AbstractEventLoop):
        self.url = url
        self.group = group
        self.consumer_name = consumer_name
        self.loop = loop
        self.redis: Optional[aioredis.Redis] = None
        self.tasks: List[asyncio.Task] = []
        self._stopped = asyncio.Event()

    async def start(self):
        if not REDIS_AVAILABLE:
            raise RuntimeError("aioredis not available")
        self.redis = await aioredis.from_url(self.url, decode_responses=True)
        logger.info("Redis client connected at %s", self.url)

    async def stop(self):
        self._stopped.set()
        for t in self.tasks:
            t.cancel()
        if self.redis:
            await self.redis.close()
        logger.info("Redis messaging stopped")

    async def publish(self, topic: str, message: Dict[str, Any]):
        if not self.redis:
            raise RuntimeError("Redis client not started")
        attempt = 0
        while True:
            try:
                await self.redis.xadd(topic, message)
                logger.debug("Published to stream %s: %s", topic, message)
                return
            except Exception as e:
                delay = exponential_backoff(attempt)
                logger.warning("XADD failed, attempt %d, retrying in %.2f: %s", attempt, delay, e)
                await asyncio.sleep(delay)
                attempt += 1

    def subscribe(self,
                  topic: str,
                  callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
                  group_id: Optional[str] = None):
        group = self.group
        consumer = self.consumer_name
        async def _consumer_task():
            assert self.redis
            # create consumer group if not exists
            try:
                await self.redis.xgroup_create(topic, group, id="$", mkstream=True)
                logger.info("Created Redis stream group=%s for %s", group, topic)
            except aioredis.exceptions.ResponseError:
                pass
            while not self._stopped.is_set():
                try:
                    entries = await self.redis.xreadgroup(group, consumer, {topic: ">"}, count=10, block=1000)
                    for stream, msgs in entries:
                        for message_id, data in msgs:
                            try:
                                payload = {k: json.loads(v) if isinstance(v, str) else v for k, v in data.items()}
                            except Exception:
                                payload = data
                            await callback(payload)
                            await self.redis.xack(topic, group, message_id)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception("Error reading from stream %s: %s", topic, e)
                    await asyncio.sleep(1)

        task = self.loop.create_task(_consumer_task())
        self.tasks.append(task)

class RabbitMQMessagingClient(MessagingClient):
    """
    RabbitMQ-based messaging using aio_pika.
    """

    def __init__(self, url: str, loop: asyncio.AbstractEventLoop):
        self.url = url
        self.loop = loop
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchanges: Dict[str, aio_pika.Exchange] = {}
        self.queues: Dict[str, aio_pika.Queue] = {}
        self.tasks: List[asyncio.Task] = []
        self._stopped = asyncio.Event()

    async def start(self):
        if not RABBITMQ_AVAILABLE:
            raise RuntimeError("aio_pika not available")
        
        self.connection = await aio_pika.connect_robust(self.url, loop=self.loop)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        logger.info("RabbitMQ client connected at %s", self.url)

    async def stop(self):
        self._stopped.set()
        for task in self.tasks:
            task.cancel()
        
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        logger.info("RabbitMQ messaging stopped")

    async def publish(self, topic: str, message: Dict[str, Any]):
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not started")
        
        # Get or create exchange for topic
        if topic not in self.exchanges:
            self.exchanges[topic] = await self.channel.declare_exchange(
                topic, aio_pika.ExchangeType.TOPIC, durable=True
            )
        
        exchange = self.exchanges[topic]
        
        attempt = 0
        while True:
            try:
                message_body = json.dumps(message).encode('utf-8')
                await exchange.publish(
                    aio_pika.Message(message_body),
                    routing_key=topic
                )
                logger.debug("Published to %s: %s", topic, message)
                return
            except Exception as e:
                delay = exponential_backoff(attempt)
                logger.warning("Publish failed, attempt %d, retrying in %.2f: %s", attempt, delay, e)
                await asyncio.sleep(delay)
                attempt += 1

    def subscribe(self,
                  topic: str,
                  callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
                  group_id: Optional[str] = None):
        
        queue_name = f"{group_id or 'default'}.{topic}"
        
        async def _consumer_task():
            if not self.channel:
                return
                
            # Declare exchange
            exchange = await self.channel.declare_exchange(
                topic, aio_pika.ExchangeType.TOPIC, durable=True
            )
            
            # Declare queue
            queue = await self.channel.declare_queue(queue_name, durable=True)
            await queue.bind(exchange, routing_key=topic)
            
            logger.info("RabbitMQ consumer started for topic=%s, queue=%s", topic, queue_name)
            
            # Use get() method instead of iterator for better compatibility
            while not self._stopped.is_set():
                try:
                    # Get message with timeout
                    message = await queue.get(timeout=1.0, fail=False)
                    if message is None:
                        continue
                        
                    try:
                        payload = json.loads(message.body.decode('utf-8'))
                        logger.debug("Received message on %s: %s", topic, payload)
                        await callback(payload)
                        await message.ack()
                    except Exception as e:
                        logger.exception("Error handling message: %s", e)
                        await message.nack(requeue=False)
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning("Error getting message from queue %s: %s", queue_name, e)
                    await asyncio.sleep(1)
            
            logger.info("RabbitMQ consumer stopped for topic=%s", topic)

        task = self.loop.create_task(_consumer_task())
        self.tasks.append(task)

def create_messaging_client(loop: Optional[asyncio.AbstractEventLoop] = None) -> MessagingClient:
    """
    Factory to create the appropriate messaging client based on environment variables.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    
    # Check for BROKER_URL first (used by RabbitMQ)
    broker_url = os.getenv("BROKER_URL")
    if broker_url and broker_url.startswith("amqp://"):
        return RabbitMQMessagingClient(url=broker_url, loop=loop)
    
    # Fall back to BROKER_TYPE for other systems
    broker_type = os.getenv("BROKER_TYPE", "kafka").lower()
    if broker_type == "kafka":
        if not KAFKA_AVAILABLE:
            raise RuntimeError("aiokafka not available")
        brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
        client_id = os.getenv("KAFKA_CLIENT_ID", "multi-agent-client")
        return KafkaMessagingClient(brokers=brokers, loop=loop, client_id=client_id)
    elif broker_type == "redis":
        if not REDIS_AVAILABLE:
            raise RuntimeError("aioredis not available")
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        group = os.getenv("REDIS_CONSUMER_GROUP", "multi-agent-group")
        consumer_name = os.getenv("REDIS_CONSUMER_NAME", "consumer-1")
        return RedisStreamMessagingClient(url=url, group=group, consumer_name=consumer_name, loop=loop)
    elif broker_type == "rabbitmq":
        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        return RabbitMQMessagingClient(url=rabbitmq_url, loop=loop)
    else:
        raise ValueError(f"Unsupported BROKER_TYPE: {broker_type}")

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