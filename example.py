import asyncio

import wreq
from httpx import AsyncClient, Timeout

from wreq_httpx_transport import WreqAsyncTransport


async def main():
    transport = WreqAsyncTransport(
        emulation=wreq.Emulation.Safari18_5,
        proxies=[wreq.Proxy.all("http://127.0.0.1:7890")],
    )

    async with AsyncClient(transport=transport) as client:
        response = await client.get(
            "https://tls.peet.ws/api/all",
            timeout=Timeout(timeout=10.0),
        )
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
