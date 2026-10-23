
import asyncio
import sys


async def main():
    print("Python:", sys.executable)

    loop = asyncio.get_running_loop()
    print("Event loop:", type(loop).__name__)

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "print('Subprocess works')",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await asyncio.wait_for(
        process.communicate(), timeout=10
    )

    print("Exit code:", process.returncode)
    print("Output:", stdout.decode().strip())

    if stderr:
        print("Error output:", stderr.decode().strip())


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )

    asyncio.run(main())
