from datetime import timedelta
from typing import AsyncIterator, Unpack

import httpx
import wreq
import wreq.exceptions


class wreqAsyncByteStream(httpx.AsyncByteStream):
    def __init__(self, response: wreq.Response) -> None:
        self.response = response
        self.streamer = response.stream()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self.streamer:  # type: ignore
            yield chunk

    async def aclose(self) -> None:
        await self.response.close()


class WreqAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        **kwargs: Unpack["wreq.ClientConfig"],
    ) -> None:
        kwargs.setdefault("cookie_store", False)
        self.client = wreq.Client(
            **kwargs,
        )

    @staticmethod
    def _map_headers(headers: httpx.Headers) -> wreq.HeaderMap:
        wreq_headers = wreq.HeaderMap()
        for k, v in headers.items():
            if k == "user-agent" and v == httpx._client.USER_AGENT:
                # ignore default httpx user-agent to let wreq set its own
                continue
            wreq_headers.append(k, v)
        return wreq_headers

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        request_params = {
            "method": getattr(wreq.Method, request.method),
            "url": str(request.url),
            "headers": self._map_headers(request.headers),
            "body": request.content,
        }

        timeouts = request.extensions.get("timeout", {})
        pool_timeout = timeouts.get("pool")
        read_timeout = timeouts.get("read")
        if pool_timeout is not None:
            request_params["timeout"] = timedelta(seconds=pool_timeout)
        if read_timeout is not None:
            request_params["read_timeout"] = timedelta(seconds=read_timeout)

        try:
            resp = await self.client.request(**request_params)
        except (
            wreq.exceptions.RustPanic,
            wreq.exceptions.TlsError,
            wreq.exceptions.BodyError,
            wreq.exceptions.BuilderError,
            wreq.exceptions.RedirectError,
            wreq.exceptions.RequestError,
            wreq.exceptions.UpgradeError,
            wreq.exceptions.StatusError,
            wreq.exceptions.WebSocketError,
        ) as e:
            raise httpx.RequestError(message=str(e.args), request=request) from e
        except (
            wreq.exceptions.ProxyConnectionError,
            wreq.exceptions.ConnectionError,
            wreq.exceptions.ConnectionResetError,
        ) as e:
            raise httpx.ConnectError(message=str(e.args), request=request) from e
        except wreq.exceptions.DecodingError as e:
            raise httpx.DecodingError(message=str(e.args), request=request) from e
        except wreq.exceptions.TimeoutError as e:
            raise httpx.TimeoutException(message=str(e.args), request=request) from e

        return httpx.Response(
            status_code=resp.status.as_int(),
            headers=httpx.Headers(resp.headers),  # type: ignore
            stream=wreqAsyncByteStream(resp),
            request=request,
        )
