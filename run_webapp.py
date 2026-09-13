#!/usr/bin/env python
"""Launch the web UI for the research and shopping agents.

Usage:
    python run_webapp.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("webapp.server:app", host="127.0.0.1", port=8787, reload=False)
