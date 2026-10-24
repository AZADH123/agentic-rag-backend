import asyncio
from app.database.session import get_session_factory
from sqlalchemy import text

async def main():
    try:
        factory = get_session_factory()
        async with factory() as session:
            r = await session.execute(text("SELECT 1"))
            print("DB Query Result:", r.scalar())
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
