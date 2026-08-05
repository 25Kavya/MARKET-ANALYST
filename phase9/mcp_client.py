import asyncio
import json
import os
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from phase1.logging_config import get_logger

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 10


class McpUnavailableError(Exception):
    """Raised when the MCP server can't be reached, times out, or the tool
    call itself fails (e.g. Groq errored) — callers should catch this and
    fall back rather than let it propagate to the user."""


def _server_url():
    port = os.getenv("MCP_SERVER_PORT", "8100")
    return f"http://127.0.0.1:{port}/mcp"


async def _call_tool_async(tool_name, arguments):
    url = _server_url()
    async with streamablehttp_client(url, timeout=_TIMEOUT_SECONDS) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            if result.isError:
                message = result.content[0].text if result.content else "unknown MCP tool error"
                raise McpUnavailableError(message)

            return json.loads(result.content[0].text)


def classify_mode_via_mcp(query, tickers, is_compare_keyword, is_portfolio_keyword):
    """Ask the MCP server (SQLite-cached, Groq-backed) to decide single/portfolio/
    compare mode. Opens a fresh short-lived connection for this one call rather
    than holding a persistent client session open."""
    start = time.monotonic()
    arguments = {
        "query": query,
        "tickers": tickers,
        "is_compare_keyword": is_compare_keyword,
        "is_portfolio_keyword": is_portfolio_keyword,
    }

    try:
        result = asyncio.run(_call_tool_async("classify_intent_mode", arguments))
    except McpUnavailableError:
        raise
    except Exception as exc:
        logger.warning("mcp_client.classify_mode_via_mcp connection failure query=%r error=%s", query, exc)
        raise McpUnavailableError(f"could not reach MCP server: {exc}") from exc

    elapsed = time.monotonic() - start
    logger.info("mcp_client.classify_mode_via_mcp ok query=%r mode=%s elapsed=%.2fs", query, result.get("mode"), elapsed)
    return result
