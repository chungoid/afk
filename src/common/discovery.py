import asyncio
import time
import uuid
import logging
from typing import List, Optional
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discovery")

class SwarmDiscovery:
    """
    Swarm-based peer discovery and distributed locking using Redis.
    Each instance registers itself periodically, allowing peers to discover each other.
    Distributed locks use Redis primitive locks for task ownership.
    """
    def __init__(
        self,
        redis_url: str,
        service_name: str,
        heartbeat_interval: float = 5.0,
        ttl: float = 15.0
    ):
        self.redis_url = redis_url
        self.service_name = service_name
        self.heartbeat_interval = heartbeat_interval
        self.ttl = ttl
        self.node_id = str(uuid.uuid4())
        self._stopped = asyncio.Event()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._redis: Optional[aioredis.Redis] = None
        self._zset_key = f"discovery:instances:{self.service_name}"

    async def start(self):
        """
        Initialize Redis and start the heartbeat loop.
        """
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        self._stopped.clear()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"[{self.service_name}] started discovery with node_id={self.node_id}")

    async def stop(self):
        """
        Stop the heartbeat loop and close Redis connection.
        """
        if self._heartbeat_task:
            self._stopped.set()
            await self._heartbeat_task
        if self._redis:
            await self._redis.close()
        logger.info(f"[{self.service_name}] stopped discovery")

    async def _heartbeat_loop(self):
        """
        Periodically announce presence and prune stale entries.
        """
        try:
            while not self._stopped.is_set():
                await self._announce()
                await asyncio.wait_for(self._stopped.wait(), timeout=self.heartbeat_interval)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.exception("Heartbeat loop error: %s", e)

    async def _announce(self):
        """
        ZADD own node_id with current timestamp, prune old ones, set expiry on zset.
        """
        now = time.time()
        try:
            pipe = self._redis.pipeline()
            pipe.zadd(self._zset_key, {self.node_id: now})
            pipe.zremrangebyscore(self._zset_key, 0, now - self.ttl)
            pipe.expire(self._zset_key, int(self.ttl * 2))
            await pipe.execute()
            logger.debug("[%s] heartbeat at %s", self.node_id, now)
        except Exception:
            logger.exception("Failed to announce heartbeat")

    async def get_peers(self) -> List[str]:
        """
        Return list of currently active peer node_ids (excluding self).
        """
        now = time.time()
        try:
            raw = await self._redis.zrangebyscore(self._zset_key, now - self.ttl, now, withscores=False)
            peers = [node for node in raw if node != self.node_id]
            logger.debug("[%s] discovered peers: %s", self.node_id, peers)
            return peers
        except Exception:
            logger.exception("Failed to get peers")
            return []

    async def acquire_lock(self, key: str, lock_ttl: float = 30.0, wait_timeout: float = 10.0) -> Optional[aioredis.lock.Lock]:
        """
        Acquire a distributed lock for a given key.
        Returns a Lock object if acquired, else None.
        """
        lock_name = f"lock:{self.service_name}:{key}"
        try:
            lock = self._redis.lock(name=lock_name, timeout=lock_ttl, blocking_timeout=wait_timeout)
            acquired = await lock.acquire()
            if acquired:
                logger.info("[%s] acquired lock %s", self.node_id, lock_name)
                return lock
            else:
                logger.warning("[%s] failed to acquire lock %s after %s seconds", self.node_id, lock_name, wait_timeout)
                return None
        except Exception:
            logger.exception("Error acquiring lock %s", lock_name)
            return None

    async def release_lock(self, lock: aioredis.lock.Lock):
        """
        Release a distributed lock.
        """
        try:
            await lock.release()
            logger.info("[%s] released lock %s", self.node_id, lock.name)
        except Exception:
            logger.exception("Error releasing lock %s", lock.name)


# Example usage:
# async def main():
#     discovery = SwarmDiscovery(redis_url="redis://localhost:6379/0", service_name="analysis-agent")
#     await discovery.start()
#     peers = await discovery.get_peers()
#     lock = await discovery.acquire_lock(key="task-123", lock_ttl=60, wait_timeout=5)
#     if lock:
#         # do work
#         await discovery.release_lock(lock)
#     await asyncio.sleep(30)
#     await discovery.stop()
# 
# if __name__ == "__main__":
#     asyncio.run(main())