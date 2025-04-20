import logging

import aiohttp
from pydantic import HttpUrl

from .core.aiohttp_trace.tracker import raise_for_status_with_json, RequestAuditor

logger = logging.getLogger(__name__)


class ClientBase:
    def __init__(self, base_url: HttpUrl | str | None = None, session: aiohttp.ClientSession | None = None, **kwargs):
        trace_configs = kwargs.get('trace_configs', [])
        trace_configs.append(RequestAuditor().get_trace_config())
        self.session = session or aiohttp.ClientSession(base_url=base_url, raise_for_status=raise_for_status_with_json,
                                                        trace_configs=trace_configs, **kwargs)

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def __del__(self):
        if not getattr(self, 'session', None) or self.session.closed:
            return
        logger.warning(
            "Client instance was not properly closed. "
            "Please use it within an 'async with' block or call `close()` explicitly."
        )
        self.session.close()
