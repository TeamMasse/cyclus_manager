import httpx
import asyncio

async def fetch_bikes():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://localhost:8000/bicycles')
        return response.json()

async def main():
    bikes_data = await fetch_bikes()
    print(bikes_data)

asyncio.run(main())