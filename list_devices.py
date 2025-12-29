import asyncio
import aiohttp
from pysmartthings import SmartThings
from getpass import getpass

async def main():
    token = token = input("Zadej SmartThings token: ")

    async with aiohttp.ClientSession() as session:
        st = SmartThings(session, token)

        devices = await st.devices()

        for device in devices:
            print(f"Name: {device.label or device.name}")
            print(f"ID:   {device.device_id}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
