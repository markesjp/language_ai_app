import asyncio


async def main() -> None:
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
