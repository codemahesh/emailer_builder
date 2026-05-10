import asyncpg
import asyncio

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host='127.0.0.1',
            user='postgres',
            password='postgres',
            database='postgres',
            timeout=5
        )
        print('✓ Connection successful!')
        await conn.close()
        return True
    except Exception as e:
        print(f'✗ Connection failed: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(test_connection())
    exit(0 if result else 1)
