from datetime import timedelta
from typing import AsyncIterator, Unpack

import httpx
import rnet
import rnet.exceptions


class RnetAsyncByteStream(httpx.AsyncByteStream):
    def __init__(self, response: rnet.Response) -> None:
        self.response = response
        self.streamer = response.stream()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self.streamer:  # type: ignore
            yield chunk

    async def aclose(self) -> None:
        await self.response.close()


class RnetAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        **kwargs: Unpack["rnet.ClientConfig"],
    ) -> None:
        kwargs.setdefault("cookie_store", False)
        self.client = rnet.Client(
            **kwargs,
        )

    @staticmethod
    def _map_headers(headers: httpx.Headers) -> rnet.HeaderMap:
        rnet_headers = rnet.HeaderMap()
        for k, v in headers.items():
            if k == "user-agent" and v == httpx._client.USER_AGENT:
                # ignore default httpx user-agent to let rnet set its own
                continue
            rnet_headers.append(k, v)
        return rnet_headers

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        request_params = {
            "method": getattr(rnet.Method, request.method),
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
            rnet.exceptions.RustPanic,
            rnet.exceptions.TlsError,
            rnet.exceptions.BodyError,
            rnet.exceptions.BuilderError,
            rnet.exceptions.RedirectError,
            rnet.exceptions.RequestError,
            rnet.exceptions.UpgradeError,
            rnet.exceptions.StatusError,
            rnet.exceptions.WebSocketError,
        ) as e:
            raise httpx.RequestError(message=str(e.args), request=request) from e
        except (
            rnet.exceptions.ProxyConnectionError,
            rnet.exceptions.ConnectionError,
            rnet.exceptions.ConnectionResetError,
        ) as e:
            raise httpx.ConnectError(message=str(e.args), request=request) from e
        except rnet.exceptions.DecodingError as e:
            raise httpx.DecodingError(message=str(e.args), request=request) from e
        except rnet.exceptions.TimeoutError as e:
            raise httpx.TimeoutException(message=str(e.args), request=request) from e

        return httpx.Response(
            status_code=resp.status.as_int(),
            headers=httpx.Headers(resp.headers),  # type: ignore
            stream=RnetAsyncByteStream(resp),
            request=request,
        )
