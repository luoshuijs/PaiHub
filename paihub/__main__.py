import asyncio

from persica.applicationbuilder import ApplicationBuilder as _ApplicationBuilder

from paihub.application import Application
from paihub.log import logger

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    uvloop = None

logger.info("Welcome to PaiHub!")

# https://docs.python.org/3.13/library/asyncio-eventloop.html#asyncio.get_event_loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


class ApplicationBuilder(_ApplicationBuilder):
    _application_class = Application


builder = ApplicationBuilder()
builder.set_scanner_package("paihub")
builder.set_loop(loop)
application = builder.build()
application.run()
