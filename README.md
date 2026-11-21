# Discord read-only MCP

This stdio MCP server exposes three tools through
[discord.py-self](https://discordpy-self.readthedocs.io/):

- `list_servers`: joined servers with `id`, `name`, and `allowed`.
- `list_channels`: channels (`id`, `name`, `type`) of an allowed server.
- `read_channel_messages`: a `messages` array with `id`, `timestamp` (ISO 8601),
  `author_id`, `author_username`, and `content`.

A channel is readable if its ID is in `DISCORD_ALLOWED_CHANNELS` or its server's
ID is in `DISCORD_ALLOWED_SERVERS`. Set either or both. Threads and forum posts
have their own channel IDs; they are readable through their server's entry.

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run
   `uv sync --locked` in this directory.
2. In Discord, enable Developer Mode under User Settings → Advanced, then
   right-click a server icon (**Copy Server ID**) or a channel (**Copy Channel ID**).
3. Create `.env` in this directory (git-ignored) and make it private with
   `chmod 600 .env`. Use the raw token with no prefix:

   ```sh
   DISCORD_USER_TOKEN=your-token
   DISCORD_ALLOWED_SERVERS=345678901234567890
   DISCORD_ALLOWED_CHANNELS=123456789012345678,234567890123456789
   ```

4. Register the server. `uv` loads `.env` on each launch, so the client config
   holds no secrets:

   ```sh
   claude mcp add discord-read-only -- uv run --locked --env-file /absolute/path/to/discord-read-only/.env --directory /absolute/path/to/discord-read-only python server.py
   ```

Ask the agent to read messages using an allowed channel ID as a string. The tool
defaults to 20 messages per call and accepts a limit of 1–100. To page backward,
use the oldest returned message ID as `before`.

Discord prohibits automating normal user accounts and may terminate them for it.
Discord still applies the account's channel permissions. The MCP allowlist
applies only to calls through this server, and the user token retains its
full account access. [Discord's self-bot policy](https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots)
