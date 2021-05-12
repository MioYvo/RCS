# __author__ = 'Mio'
import logging
import signal
import sys
from pathlib import Path

import tornado.escape
import tornado.ioloop
import tornado.web
from tornado.options import options

sys.path.insert(0, str(Path().absolute().parent))

from config.clients import ioloop
from Access.app import app
from config import PROJECT_NAME


# noinspection PyUnusedLocal
def signal_handler(sig, frame):
    """Triggered when a signal is received from system."""
    _ioloop = tornado.ioloop.IOLoop.current()

    def shutdown():
        """Force server and ioloop shutdown."""
        logging.info('Shutting down server')
        # logging.info('Terminating db connection pool')
        # if app.pool:
        #     app.pool.terminate()
        #     logging.info('Terminated db connection pool')
        if app.amqp_connection:
            logging.info('Closing amqp connection')
            _ioloop.asyncio_loop.create_task(app.amqp_connection.close())
        if app.m_client:
            logging.info('Closing mongo connection')
            app.m_client.close()
        _ioloop.stop()
        logging.info('Bye')

    logging.warning('Caught signal: %s', sig)
    _ioloop.add_callback_from_signal(shutdown)


def main():
    # init db
    app.listen(options.port)
    logging.info(f"{PROJECT_NAME} run on: http://localhost:{options.port}")
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    ioloop.run_forever()


if __name__ == "__main__":
    main()
