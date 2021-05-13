# coding=utf-8
# __author__ = 'Mio'
from typing import List, Callable, Optional, Union, Tuple

from aio_pika import Connection, Exchange, Channel
from aio_pika.queue import ConsumerTag, Queue


async def make_consumer(
        amqp_connection: Connection,
        consume: Callable,
        queue_name: str,
        prefetch_count: int,
        exchange: Union[Exchange, str] = '',
        routing_key: str = '',
        consumer_count: int = 1,
        durable: bool = False,
        auto_delete: bool = False,
        passive: bool = False,
        max_priority: Optional[int] = 20,
) -> Tuple[List[ConsumerTag], List[Channel]]:
    consumers = []
    consumer_channels = []
    for _ in range(consumer_count):
        channel = await amqp_connection.channel()
        await channel.set_qos(prefetch_count=prefetch_count)
        arguments = {
            "x-max-priority": max_priority
        } if max_priority else None
        queue: Queue = await channel.declare_queue(
            name=queue_name, durable=durable, auto_delete=auto_delete,
            passive=passive, arguments=arguments
        )
        if exchange:
            await queue.bind(exchange=exchange, routing_key=routing_key)
        consumers.append(await queue.consume(consume))
        consumer_channels.append(channel)
    return consumers, consumer_channels
