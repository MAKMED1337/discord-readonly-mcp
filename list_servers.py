"""List joined Discord servers: uv run --env-file .env python list_servers.py"""

import asyncio
import os

import discord


async def main() -> None:
    async with discord.Client() as client:
        await client.login(os.environ["DISCORD_USER_TOKEN"].strip())
        for guild in await client.fetch_guilds(with_counts=False):
            print(f"{guild.id}\t{guild.name}")


if __name__ == "__main__":
    asyncio.run(main())
