import asyncio

from paihub.application import Application
from paihub.log import logger

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    uvloop = None


application = Application()
logger.info("Welcome to PaiHub!")
application.run()
