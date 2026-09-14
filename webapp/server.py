"""Web frontend for the research and shopping agents.

Serves a single-page UI and streams each agent's progress log over a
WebSocket while it runs, then delivers the final result (report markdown,
or order summary + screenshot/video URLs).
"""

import asyncio
import queue
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from research_agent.agent import run as research_run
from research_agent.shop_agent import run as shop_run

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
RUNS_DIR = BASE_DIR / "runs"
RUNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Anakai Agents")
app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


async def _run_streaming(websocket: WebSocket, fn):
    """Run fn(log=...) in a background thread and stream {type: log|done|error}
    messages to the websocket as they happen."""
    log_q: "queue.Queue[dict]" = queue.Queue()

    def worker():
        try:
            result = fn(log=lambda msg: log_q.put({"type": "log", "message": str(msg)}))
            log_q.put({"type": "done", "result": result})
        except Exception as e:
            log_q.put({"type": "error", "message": str(e)})

    threading.Thread(target=worker, daemon=True).start()

    while True:
        msg = await asyncio.to_thread(log_q.get)
        await websocket.send_json(msg)
        if msg["type"] in ("done", "error"):
            break


@app.websocket("/ws/research")
async def ws_research(websocket: WebSocket):
    await websocket.accept()
    try:
        params = await websocket.receive_json()
        question = (params.get("question") or "").strip()
        sources = int(params.get("sources") or 4)
        if not question:
            await websocket.send_json({"type": "error", "message": "Please enter a question."})
            return
        await _run_streaming(
            websocket,
            lambda log: research_run(question, sources_per_query=sources, log=log),
        )
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass


@app.websocket("/ws/shop")
async def ws_shop(websocket: WebSocket):
    await websocket.accept()
    try:
        params = await websocket.receive_json()
        want = (params.get("want") or "").strip()
        if not want:
            await websocket.send_json({"type": "error", "message": "Please describe what you want to buy."})
            return

        run_id = uuid.uuid4().hex[:10]
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = run_dir / "confirmation.png"
        video_path = run_dir / "session.webm"
        want_record = bool(params.get("record", True))

        def call(log):
            result = shop_run(
                want,
                buyer_first_name=params.get("first_name") or "Anakin",
                buyer_last_name=params.get("last_name") or "Forge",
                buyer_zip=params.get("zip") or "94107",
                screenshot_path=str(screenshot_path),
                log=log,
                headless=True,
                slow_mo_ms=700,
                record=want_record,
                video_path=str(video_path),
                use_anakin_browser=True,
            )
            result = dict(result)
            result["screenshot_url"] = f"/runs/{run_id}/confirmation.png" if screenshot_path.exists() else None
            result["video_url"] = f"/runs/{run_id}/session.webm" if result.get("video") else None
            return result

        await _run_streaming(websocket, call)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
