import threading
import time

import pytest
import requests
import uvicorn

from phase6.api import app as fastapi_app


class _NoSignalServer(uvicorn.Server):
    """uvicorn installs OS signal handlers by default, which only works on
    the main thread — this runs the server inside a background thread for
    the duration of a test session, so signal handling must be disabled."""

    def install_signal_handlers(self):
        pass


@pytest.fixture(scope="session")
def live_server_url():
    host, port = "127.0.0.1", 8765
    config = uvicorn.Config(fastapi_app, host=host, port=port, log_level="warning")
    server = _NoSignalServer(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"
    for _ in range(50):
        try:
            if requests.get(f"{base_url}/health", timeout=0.5).status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.2)
    else:
        raise RuntimeError("phase6 test server did not start in time")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)
