#!/usr/bin/env python
"""Launch the Geotech AI API on the first free port at/after 8000.

Usage:  python run.py
The frontend auto-discovers whichever port this lands on (see frontend/src/api.js).
"""
import socket

import uvicorn

START_PORT = 8000
MAX_TRIES = 20


def find_free_port(start: int = START_PORT, tries: int = MAX_TRIES) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue  # in use, try the next one
    raise RuntimeError(f"No free port in range {start}..{start + tries - 1}")


if __name__ == "__main__":
    port = find_free_port()
    if port != START_PORT:
        print(f"[run] port {START_PORT} is busy — using {port} instead")
    print(f"[run] API on http://127.0.0.1:{port}   (Swagger UI: /docs)")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)