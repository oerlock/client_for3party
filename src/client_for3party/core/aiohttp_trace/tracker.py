import logging
import traceback
from types import SimpleNamespace
from typing import Tuple, Optional

from aiohttp import TraceConfig, ClientSession, TraceRequestExceptionParams, TraceRequestChunkSentParams, \
    ClientResponseError, ClientResponse, RequestInfo, ContentTypeError
from datetime import datetime

from multidict import MultiMapping



class ClientResponseErrorWithMore(ClientResponseError):
    def __init__(
            self,
            request_info: RequestInfo,
            history: Tuple[ClientResponse, ...],
            *,
            code: Optional[int] = None,
            status: Optional[int] = None,
            message: str = "",
            headers: Optional[MultiMapping[str]] = None,
            data_received: dict | None = None,
    ) -> None:
        super().__init__(request_info, history, code=code, status=status, message=message, headers=headers)
        self.data_received = data_received

    def __repr__(self) -> str:
        args = f"status={self.status!r}" if self.status != 0 else ''
        args += f", message={self.message!r}" if self.message != '' else ''
        args += f", data_received={self.data_received!r}" if self.data_received is not None else ''
        args += f", {self.request_info!r}, {self.history!r}"
        return f"{type(self).__name__}({args})"


async def raise_for_status_with_json(resp: ClientResponse):
    if 400 > resp.status:
        return
    content_type = resp.headers.get('Content-Type', '')
    try:
        data_received = await resp.json() if 'application/json' in content_type else None
    except ContentTypeError as e:
        data_received = None
    if hasattr(resp, '_in_context') and not resp._in_context:
        resp.release()
    raise ClientResponseErrorWithMore(
        resp.request_info,
        resp.history,
        status=resp.status,
        message=resp.reason,
        headers=resp.headers,
        data_received=data_received,
    )


class RequestAuditor:
    def __init__(self, logger=None, include_stack_trace=False):
        """
        Initialize the auditor class.
        :param logger: Custom logger. If None, the default logger will be used.
        :param include_stack_trace: Whether to log the exception's stack trace.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.include_stack_trace = include_stack_trace

    def _log(self, message: str, level=logging.INFO):
        """
        Internal method for logging messages.
        :param message: The log message to record.
        :param level: Log level (default is INFO).
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        if level == logging.ERROR:
            self.logger.error(full_message)
        else:
            self.logger.info(full_message)

    def get_trace_config(self) -> TraceConfig:
        """
        Returns a TraceConfig instance with audit hooks.
        """
        trace_config = TraceConfig()
        trace_config.on_request_chunk_sent.append(self.on_request_chunk_sent)
        trace_config.on_request_exception.append(self.on_request_exception)
        return trace_config

    def __call__(self, *args, **kwargs):
        return {
            'raise_for_status': raise_for_status_with_json,
            'trace_configs': [self.get_trace_config()],
        }

    async def on_request_chunk_sent(self, session: ClientSession, trace_config_ctx: SimpleNamespace,
                                    params: TraceRequestChunkSentParams):
        """
        Hook to handle data sent during a request.
        """
        trace_config_ctx.data_sent = params.chunk[:512]

    async def on_request_exception(self, session: ClientSession, trace_config_ctx: SimpleNamespace,
                                   params: TraceRequestExceptionParams):
        """
        Audit logic for request exceptions.
        """
        try:
            # Basic exception information
            msg = f"{params.exception!r}\n"
            msg += f'Data Sent: {trace_config_ctx.data_sent}\n' if hasattr(trace_config_ctx, 'data_sent') else ""

            # Log full stack trace if required
            if self.include_stack_trace:
                stack_trace = "".join(
                    traceback.format_exception(None, params.exception, params.exception.__traceback__)
                )
                msg += f"\nStack Trace:\n{stack_trace}"

            self._log(msg, level=logging.ERROR)
        except Exception as e:
            self._log(f"Error in on_request_exception: {e!r}", level=logging.ERROR)
