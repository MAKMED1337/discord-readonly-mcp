"""Join a Discord server: uv run python join_guild.py <guild_id | invite code | discord.gg URL>"""

import asyncio
import os
import sys

import discord


async def main(target: str) -> None:
    token = os.environ["DISCORD_USER_TOKEN"].strip()
    async with discord.Client() as client:
        await client.login(token)
        # all-digit input is treated as a guild ID; a numeric vanity invite would be misread.
        if target.isdigit():
            guild = await client.join_guild(int(target))
            print(f"Joined {guild.name} ({guild.id})")
        else:
            invite = await client.accept_invite(target)
            print(f"Accepted invite {invite.code} for {getattr(invite.guild, 'name', 'unknown')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python join_guild.py <guild_id | invite code | discord.gg URL>")
    try:
        asyncio.run(main(sys.argv[1].strip()))
    except discord.NotFound:
        raise SystemExit("Not found: invalid/expired invite, or server ID not discoverable (use an invite).")
    except discord.CaptchaRequired:
        raise SystemExit("Discord asked for a captcha. Join in the Discord app instead.")
    except discord.HTTPException as error:
        raise SystemExit(f"Discord returned HTTP {error.status}: {error.text}")
