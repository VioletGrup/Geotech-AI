#!/usr/bin/env python
"""Launch the Geotech AI API on any free port.

Tries 8000 first, then 8001..8010, then falls back to whatever free port the
OS hands out — so it always starts even if the whole 8000 band is busy.
The chosen port is written to frontend/.env.local as VITE_API_BASE, so the
frontend follows the backend to any port (see frontend/src/api.js).

Usage:  python run.py
"""
import pathlib
import socket

import uvicorn

PREFERRED_RANGE = range(8000, 8011)  # 8000..8010 — matches the frontend probe band


def _free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_free_port() -> int:
    # 1) prefer the well-known band the frontend probes
    for port in PREFERRED_RANGE:
        if _free(port):
            return port
    # 2) all busy — let the OS assign any free ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def write_frontend_env(port: int) -> None:
    """Point the frontend at this port. Written every run so it never goes stale."""
    frontend = pathlib.Path(__file__).resolve().parent / "frontend"
    if not frontend.is_dir():
        return
    (frontend / ".env.local").write_text(f"VITE_API_BASE=http://localhost:{port}\n")


if __name__ == "__main__":
    port = find_free_port()
    if port not in PREFERRED_RANGE:
        print(f"[run] 8000-8010 all busy — using OS-assigned port {port}")
    elif port != 8000:
        print(f"[run] port 8000 busy — using {port} instead")
    write_frontend_env(port)
    print(f"[run] API on http://127.0.0.1:{port}   (Swagger UI: /docs)")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)