#!/usr/bin/env bash
set -e

python -m phase9.mcp_server &

for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${MCP_SERVER_PORT:-8100}/mcp" -o /dev/null 2>/dev/null; then
    break
  fi
  sleep 0.5
done

exec uvicorn phase6.api:app --host 0.0.0.0 --port "${PORT:-8000}"
