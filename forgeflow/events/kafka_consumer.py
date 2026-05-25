"""Kafka consumer — same dispatcher, different transport.

Shipped as a thin stub on top of aiokafka. The lifecycle mirrors
RedisStreamsConsumer so the lifespan code in api/main.py can swap them
based on settings.events_provider.

Note: deliberately lighter than the Redis consumer. Kafka tuning
(partition assignment strategy, max-poll-interval, isolation_level,
SASL/SSL configs) is intentionally left to callers via the `extra`
dict — wiring every option here would be premature and brittle.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from forgeflow.events.dispatcher import EventDispatcher

logger = logging.getLogger(__name__)


class KafkaConsumer:
    def __init__(
        self,
        dispatcher: EventDispatcher,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.dispatcher = dispatcher
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.extra = extra or {}
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._consumer: Any = None

    async def start(self) -> None:
        if self._task is not None:
            return
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "Kafka support requires the 'events-kafka' extra. "
                "Install with: pip install 'forgeflow[events-kafka]'"
            ) from exc

        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=False,        # commit per successful dispatch
            auto_offset_reset="latest",
            **self.extra,
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "KafkaConsumer started | topic=%s group_id=%s servers=%s",
            self.topic,
            self.group_id,
            self.bootstrap_servers,
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
        if self._consumer is not None:
            try:
                await self._consumer.stop()
            except Exception:
                pass
            self._consumer = None
        logger.info("KafkaConsumer stopped")

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                msg = await self._consumer.getone()
            except Exception as exc:
                if self._stop.is_set():
                    return
                logger.exception("Kafka getone() failed: %s", exc)
                await asyncio.sleep(1)
                continue

            await self._handle(msg)

    async def _handle(self, msg: Any) -> None:
        msg_id = f"{msg.topic}@{msg.partition}:{msg.offset}"
        raw = msg.value.decode("utf-8") if isinstance(msg.value, bytes) else str(msg.value)

        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("event %s invalid JSON: %s; committing + dropping", msg_id, exc)
            await self._commit()
            return

        try:
            trigger = EventDispatcher.parse_event(envelope, source_event_id=msg_id)
        except ValueError as exc:
            logger.warning("event %s rejected: %s; committing + dropping", msg_id, exc)
            await self._commit()
            return

        result = await self.dispatcher.dispatch(trigger)
        if result.ok:
            await self._commit()
        else:
            logger.error("event %s dispatch failed; NOT committing: %s", msg_id, result.error)
            # Leaving offset uncommitted means the next consumer poll re-reads;
            # that's safe at-least-once. For poison messages, operators should
            # advance the offset manually via kafka-consumer-groups.sh.

    async def _commit(self) -> None:
        try:
            await self._consumer.commit()
        except Exception as exc:
            logger.warning("Kafka commit failed: %s", exc)
