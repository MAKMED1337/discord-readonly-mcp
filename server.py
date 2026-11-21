import asyncio
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import discord
from curl_cffi import CurlError
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field


class DiscordMessage(BaseModel):
    id: str
    timestamp: datetime
    author_id: str
    author_username: str
    content: str


class ReadChannelMessagesResult(BaseModel):
    messages: list[DiscordMessage]


class DiscordServer(BaseModel):
    id: str
    name: str
    allowed: bool


class ListServersResult(BaseModel):
    servers: list[DiscordServer]


class DiscordChannel(BaseModel):
    id: str
    name: str
    type: str


class ListChannelsResult(BaseModel):
    channels: list[DiscordChannel]


def is_snowflake(value: str) -> bool:
    return bool(re.fullmatch(r"[1-9][0-9]{0,19}", value)) and int(value) < 2**64


def id_set(variable: str) -> frozenset[str]:
    values = frozenset(
        value.strip()
        for value in os.environ.get(variable, "").split(",")
        if value.strip()
    )
    if not all(is_snowflake(value) for value in values):
        raise SystemExit(f"Set {variable} to comma-separated Discord IDs.")
    return values


token = os.environ.pop("DISCORD_USER_TOKEN", "").strip()
if not token or any(not 33 <= ord(character) <= 126 for character in token):
    raise SystemExit("Set DISCORD_USER_TOKEN to the raw Discord user token.")

allowed_channels = id_set("DISCORD_ALLOWED_CHANNELS")
allowed_servers = id_set("DISCORD_ALLOWED_SERVERS")
if not allowed_channels and not allowed_servers:
    raise SystemExit("Set DISCORD_ALLOWED_CHANNELS and/or DISCORD_ALLOWED_SERVERS.")

mcp = FastMCP("discord-read-only")
read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


@asynccontextmanager
async def discord_client() -> AsyncIterator[discord.Client]:
    try:
        async with discord.Client() as client:
            async with asyncio.timeout(15):
                await client.login(token)
                yield client
    except discord.LoginFailure:
        raise ToolError("Discord rejected the user token.") from None
    except discord.HTTPException as error:
        raise ToolError(f"Discord returned HTTP {error.status}.") from None
    except (CurlError, OSError):
        raise ToolError("Could not reach Discord or the request timed out.") from None


def require_snowflake(name: str, value: str) -> int:
    if not is_snowflake(value):
        raise ToolError(f"{name} must be a Discord ID.")
    return int(value)


@mcp.tool(annotations=read_only)
async def list_servers() -> ListServersResult:
    """List servers the account has joined. Only `allowed` servers can be browsed or read."""
    async with discord_client() as client:
        guilds = await client.fetch_guilds(with_counts=False)
        return ListServersResult(
            servers=[
                DiscordServer(
                    id=str(g.id), name=g.name, allowed=str(g.id) in allowed_servers
                )
                for g in guilds
            ]
        )


@mcp.tool(annotations=read_only)
async def list_channels(
    server_id: Annotated[
        str, Field(description="An explicitly allowed Discord server ID.")
    ],
) -> ListChannelsResult:
    """List a server's channels (no categories or threads), in sidebar order."""
    guild_id = require_snowflake("server_id", server_id)
    if server_id not in allowed_servers:
        raise ToolError("This server is not on the server's allowlist.")
    async with discord_client() as client:
        guild = await client.fetch_guild(guild_id, with_counts=False)
        channels = sorted(await guild.fetch_channels(), key=lambda c: c.position)
        return ListChannelsResult(
            channels=[
                DiscordChannel(id=str(c.id), name=c.name, type=str(c.type))
                for c in channels
                if not isinstance(c, discord.CategoryChannel)
            ]
        )


@mcp.tool(annotations=read_only)
async def read_channel_messages(
    channel_id: Annotated[
        str,
        Field(
            description="A Discord channel ID that is allowed itself or via its server."
        ),
    ],
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
    before: Annotated[
        str | None,
        Field(description="Return messages older than this Discord message ID."),
    ] = None,
) -> ReadChannelMessagesResult:
    """Read messages from an allowed Discord channel, newest first."""
    channel_snowflake = require_snowflake("channel_id", channel_id)
    if channel_id not in allowed_channels and not allowed_servers:
        raise ToolError("This channel is not on the server's allowlist.")
    before_message = (
        discord.Object(id=require_snowflake("before", before))
        if before is not None
        else None
    )

    async with discord_client() as client:
        channel: discord.abc.Messageable
        if channel_id in allowed_channels:
            channel = client.get_partial_messageable(channel_snowflake)
        else:
            fetched = await client.fetch_channel(channel_snowflake)
            guild = getattr(fetched, "guild", None)
            if guild is None or str(guild.id) not in allowed_servers:
                raise ToolError("This channel is not on the server's allowlist.")
            if not isinstance(fetched, discord.abc.Messageable):
                raise ToolError(
                    f"This {fetched.type} channel has no messages; read its threads or posts instead."
                )
            channel = fetched
        messages = [
            DiscordMessage(
                id=str(message.id),
                timestamp=message.created_at,
                author_id=str(message.author.id),
                author_username=message.author.name,
                content=message.content,
            )
            async for message in channel.history(
                limit=limit, before=before_message, oldest_first=False
            )
        ]
        return ReadChannelMessagesResult(messages=messages)


if __name__ == "__main__":
    mcp.run(transport="stdio")
