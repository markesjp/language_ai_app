import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://language_user:language_pass@localhost:5433/language_ai')
    try:
        rows = await conn.fetch('SELECT * FROM runtime_settings;')
        for row in rows:
            print(dict(row))
    except Exception as e:
        print("Error:", e)
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
