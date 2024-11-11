import inspect
import logging

import aiohttp
from pydantic import HttpUrl

logger = logging.getLogger(__name__)


class ClientBase:
    def __init__(self, base_url: HttpUrl, session: aiohttp.ClientSession | None = None):
        self.base_url = base_url
        self.session = session or aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def __del__(self):
        if self.session.closed:
            return
        logger.warning(
            "ClientResolvePay instance was not properly closed. "
            "Please use it within an 'async with' block or call `close()` explicitly."
        )
        self.session.close()

    @staticmethod
    async def is_success(resp: aiohttp.ClientResponse, resp_params: dict | None = None) -> bool:
        try:
            resp.raise_for_status()
        except aiohttp.ClientResponseError as e:
            # Get the current call stack information
            stack = inspect.stack()
            # Retrieve information about the caller in the stack
            caller = stack[
                1]  # stack[0] contains the current function's information, stack[1] refers to the caller's location
            file_name = caller.filename
            line_number = caller.lineno
            msg_resp = await resp.text()
            logger.error(f'{file_name}:{line_number}: {e}\n\t{msg_resp=}\n\t{resp.request_info=}')
            if resp_params is not None:
                logger.debug(f'{resp_params=}')
            return False
        return True
