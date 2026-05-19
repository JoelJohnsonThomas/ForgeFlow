"""A2A transport layer — InMemoryTransport for intra-process, HTTPTransport stub for remote.

In a production multi-process deployment, switch to HTTPTransport which calls
the /a2a/message endpoint on each agent's host. The registry stores endpoints
as URLs in that case.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from forgeflow.a2a.protocol import A2AMessage, A2ATask, A2AArtifact

logger = logging.getLogger(__name__)


class BaseTransport(ABC):
    @abstractmethod
    async def send(self, message: A2AMessage, endpoint: str) -> A2AMessage | None:
        """Send a message to an agent endpoint and return the response."""


class InMemoryTransport(BaseTransport):
    """Routes messages within the same process via an asyncio queue per agent."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def get_queue(self, agent_id: str) -> asyncio.Queue:
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue(maxsize=100)
        return self._queues[agent_id]

    async def send(self, message: A2AMessage, endpoint: str) -> A2AMessage | None:
        agent_id = endpoint.replace("internal://", "")
        queue = self.get_queue(agent_id)
        await queue.put(message)
        logger.debug("InMemoryTransport: sent %s to %s", message.method, agent_id)
        return None  # Fire-and-forget in the in-memory case

    async def receive(self, agent_id: str, timeout: float = 5.0) -> A2AMessage | None:
        queue = self.get_queue(agent_id)
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


class HTTPTransport(BaseTransport):
    """Sends A2A messages over HTTP (for multi-process or multi-host deployments)."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def send(self, message: A2AMessage, endpoint: str) -> A2AMessage | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{endpoint}/a2a/message",
                    json=message.model_dump(mode="json"),
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return A2AMessage(**response.json())
        except Exception as e:
            logger.error("HTTPTransport send failed to %s: %s", endpoint, e)
            return None


# Global singleton transport (in-memory for this deployment)
_transport: BaseTransport | None = None


def get_transport() -> BaseTransport:
    global _transport
    if _transport is None:
        _transport = InMemoryTransport()
    return _transport
