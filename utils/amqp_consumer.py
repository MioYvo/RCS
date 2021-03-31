# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/31/21 5:07 AM
from aio_pika import IncomingMessage
from utils.logger import Logger


class AmqpConsumer:
    logger = Logger(name='AmqpConsumer')
    outing_key = ""

    def __init__(self, amqp_connection):
        self.amqp_connection = amqp_connection

    @classmethod
    async def ack(cls, msg: IncomingMessage) -> None:
        if isinstance(msg, IncomingMessage):
            try:
                await msg.ack()
            except Exception as e:
                cls.logger.error(e)

    @classmethod
    async def reject(cls, msg: IncomingMessage, requeue: bool = False) -> None:
        if isinstance(msg, IncomingMessage):
            try:
                await msg.reject(requeue=requeue)
            except Exception as e:
                cls.logger.error(e)

    async def consume(self, message: IncomingMessage):
        raise NotImplementedError
