"""Event-driven workflow triggers — Redis Streams + Kafka adapters."""

from forgeflow.events.dispatcher import EventDispatcher, WorkflowTrigger
from forgeflow.events.redis_consumer import RedisStreamsConsumer

__all__ = ["EventDispatcher", "RedisStreamsConsumer", "WorkflowTrigger"]
