"""Self-hosts the FastAPI backend + MCP server inside this same process,
for platforms (like Streamlit Community Cloud) that only run one service.

Only used when MARKET_ANALYST_SELF_HOST_BACKEND is set — local dev and the
test suite start phase6/api.py and phase9/mcp_server.py as separate
processes themselves, per the README, and never set that flag.
"""
import os
import subprocess
import sys
import time

import requests
import streamlit as st

_HEALTH_URL = "http://127.0.0.1:8000/health"
_SECRET_NAMES = ("GROQ_API_KEY", "GROQ_MODEL", "MCP_SERVER_PORT", "LOG_LEVEL")


def _propagate_secrets():
    try:
        secrets = st.secrets
    except Exception:
        return
    for name in _SECRET_NAMES:
        if name not in os.environ:
            try:
                os.environ[name] = str(secrets[name])
            except (KeyError, FileNotFoundError):
                pass


@st.cache_resource(show_spinner="Starting backend...")
def ensure_backend_running():
    _propagate_secrets()

    subprocess.Popen([sys.executable, "-m", "phase9.mcp_server"])
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "phase6.api:app",
        "--host", "127.0.0.1", "--port", "8000",
    ])

    for _ in range(40):
        try:
            if requests.get(_HEALTH_URL, timeout=1).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False
