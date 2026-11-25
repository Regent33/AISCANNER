import os, socket, subprocess, sys, time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("SCANNER_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(data):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Server:
    """Real uvicorn subprocess, so tests can hard-kill it."""
    def __init__(self, data_dir, env=None):
        self.port, self.data, self.env = free_port(), data_dir, env or {}
        self.proc = None

    def start(self):
        env = {**os.environ, "SCANNER_DATA": str(self.data), **self.env}
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "backend"),
                                      "--port", str(self.port), "--log-level", "warning"], env=env, cwd=ROOT)
        for _ in range(200):
            try:
                if httpx.get(self.url("/api/health"), timeout=1).status_code == 200:
                    return self
            except httpx.HTTPError:
                time.sleep(0.1)
        raise RuntimeError("server did not start")

    def url(self, p):
        return f"http://127.0.0.1:{self.port}{p}"

    def kill(self):
        self.proc.kill(); self.proc.wait()


@pytest.fixture
def server(data):
    servers = []
    def make(**env):
        s = Server(data, env); servers.append(s); return s
    yield make
    for s in servers:
        if s.proc and s.proc.poll() is None:
            s.kill()
