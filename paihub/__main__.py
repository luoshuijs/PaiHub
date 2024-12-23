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


class ApplicationBuilder(_ApplicationBuilder):
    _application_class = Application


builder = ApplicationBuilder()
builder.set_scanner_package("paihub")
application = builder.build()
application.run()
