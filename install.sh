#!/usr/bin/env bash
# Register this MCP server globally with coding agents via add-mcp.
# Usage: ./install.sh [path-to-discord-read-only] [add-mcp options, e.g. -a claude-code -a codex -y]
# Without -a, add-mcp asks which agents to install to.
set -euo pipefail

dir=$PWD
if [[ $# -gt 0 && $1 != -* ]]; then
  dir=$1
  shift
fi
dir=$(realpath "$dir")

# ponytail: add-mcp splits the command on spaces, so the path must not contain any.
if [[ $dir == *" "* ]]; then
  echo "Path must not contain spaces: $dir" >&2
  exit 1
fi
if [[ ! -f $dir/server.py ]]; then
  echo "No server.py in $dir" >&2
  exit 1
fi
if [[ ! -f $dir/.env ]]; then
  echo "Create $dir/.env first (see README)." >&2
  exit 1
fi

uv sync --locked --directory "$dir"
npx -y add-mcp@2.6.1 \
  "uv run --locked --env-file $dir/.env --directory $dir python server.py" \
  --name discord-read-only --global "$@"
