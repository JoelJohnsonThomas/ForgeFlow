"""Redis Streams consumer — reads workflow trigger events and dispatches.

Why Redis Streams over Kafka for the default consumer:
  - ships in most clusters via redis-stack or an Operator
  - native consumer-group semantics (XREADGROUP) give at-least-once delivery
  - lightweight: no Zookeeper / KRaft / partition rebalancing concerns
  - perfect for the throughput a single ForgeFlow deployment will see

For Kafka, see kafka_consumer.py (separate optional extra). Same dispatcher
on the receive side — only the consumer differs.

Consumer-group flow:
  1. Create the stream + group at startup (idempotent)
  2. XREADGROUP loops, blocking briefly between iterations so SIGTERM lands
  3. Each event is parsed + dispatched; success -> XACK; failure -> leave
     in pending so retry happens via XCLAIM or manual claim by an operator

Configuration (settings.py):
  events_redis_enabled       bool      default False
  events_redis_url           str       redis://localhost:6379/0
  events_redis_stream        str       default 'forgeflow:workflows'
  events_redis_group         str       default 'forgeflow'
  events_redis_consumer      str       default <hostname>
  events_redis_block_ms      int       default 5000
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from forgeflow.events.dispatcher import EventDispatcher

logger = logging.getLogger(__name__)


class RedisStreamsConsumer:
    """Long-running task that pulls events from a Redis stream and dispatches.

    Construct with a dispatcher; call start() to spawn the background task,
    stop() during shutdown.
    """

    def __init__(
        self,
        dispatcher: EventDispatcher,
        redis_url: str,
        stream: str,
        group: str,
        consumer_name: str,
        block_ms: int = 5000,
        batch_size: int = 10,
    ) -> None:
        self.dispatcher = dispatcher
        self.redis_url = redis_url
        self.stream = stream
        self.group = group
        self.consumer_name = consumer_name
        self.block_ms = max(100, block_ms)
        self.batch_size = max(1, batch_size)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._client: Any = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._client = await self._connect()
        await self._ensure_group()
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "RedisStreamsConsumer started | stream=%s group=%s consumer=%s",
            self.stream,
            self.group,
            self.consumer_name,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
        logger.info("RedisStreamsConsumer stopped")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _connect(self) -> Any:
        try:
            import redis.asyncio as redis  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "Redis support requires the 'events' extra. "
                "Install with: pip install 'forgeflow[events]'"
            ) from exc
        return redis.from_url(self.redis_url, decode_responses=True)

    async def _ensure_group(self) -> None:
        """Create the consumer group if it doesn't exist. Idempotent."""
        try:
            await self._client.xgroup_create(
                self.stream, self.group, id="0", mkstream=True
            )
            logger.info("Created Redis consumer group %s on %s", self.group, self.stream)
        except Exception as exc:
            # BUSYGROUP means the group already exists — fine.
            if "BUSYGROUP" not in str(exc).upper():
                raise

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                response = await self._client.xreadgroup(
                    self.group,
                    self.consumer_name,
                    {self.stream: ">"},
                    count=self.batch_size,
                    block=self.block_ms,
                )
            except Exception as exc:
                logger.exception("XREADGROUP failed: %s", exc)
                await asyncio.sleep(1)
                continue

            if not response:
                continue  # block timeout, no messages

            for _stream_name, messages in response:
                for msg_id, fields in messages:
                    await self._handle(msg_id, fields)

    async def _handle(self, msg_id: str, fields: dict[str, str]) -> None:
        """Parse + dispatch a single event. Success -> XACK; failure -> leave
        pending so an operator can XCLAIM and inspect."""
        raw_payload = fields.get("payload") or fields.get("data")
        if not raw_payload:
            logger.warning("event %s missing 'payload' field; acking + dropping", msg_id)
            await self._ack(msg_id)
            return

        try:
            envelope = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            logger.warning("event %s payload is not JSON: %s; acking + dropping", msg_id, exc)
            await self._ack(msg_id)
            return

        try:
            trigger = EventDispatcher.parse_event(envelope, source_event_id=msg_id)
        except ValueError as exc:
            logger.warning("event %s rejected: %s; acking + dropping", msg_id, exc)
            await self._ack(msg_id)
            return

        result = await self.dispatcher.dispatch(trigger)
        if result.ok:
            await self._ack(msg_id)
        else:
            # Pipeline-level failures stay pending. An operator can decide
            # to XCLAIM + retry or XACK after inspecting; we don't auto-retry
            # because LLM cost makes naive retry loops dangerous.
            logger.error("event %s dispatch failed; leaving pending: %s", msg_id, result.error)

    async def _ack(self, msg_id: str) -> None:
        try:
            await self._client.xack(self.stream, self.group, msg_id)
        except Exception as exc:
            logger.warning("XACK %s failed: %s", msg_id, exc)
