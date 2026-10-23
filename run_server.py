
import asyncio
import sys

import uvicorn


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )

    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        loop="asyncio",
        reload=False,
    )

    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
