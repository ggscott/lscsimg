from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import asyncio
import json
import logging
import re
import redis.asyncio as redis
from contextlib import asynccontextmanager

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

# Mount static files directory
# We'll serve the main HTML from a specific route, but JS/CSS from /static
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Redis Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class RenderRequest(BaseModel):
    data: Optional[Dict[str, Any]] = None
    previousData: Optional[Dict[str, Any]] = None
    regionName: str = "Unknown Region"
    type: str = "sim" # "sim" or "zone"
    primsHistory: Optional[List[int]] = None

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/")
@app.post("/render")
async def render(request: Request, payload: RenderRequest):
    data = payload.data or {}
    regionName = payload.regionName
    render_type = payload.type
    primsHistory = payload.primsHistory

    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', regionName)
    channel_name = f"region:{safe_name}:{render_type}"
    latest_key = f"latest:{safe_name}:{render_type}"

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    scheme = forwarded_proto if forwarded_proto else ("https" if request.url.scheme == "https" else "http")
    host = forwarded_host if forwarded_host else request.headers.get("host", "localhost:8000")
    base_url = f"{scheme}://{host}"

    # Prepare the payload for the frontend (ignoring previousData)
    frontend_payload = {
        "data": data,
        "regionName": regionName,
        "type": render_type,
        "primsHistory": primsHistory
    }

    payload_json = json.dumps(frontend_payload)

    # Save to Redis and publish
    await redis_client.set(latest_key, payload_json)
    await redis_client.publish(channel_name, payload_json)

    # Return the permanent view URL for this region
    response_json = {"url": f"{base_url}/view/{safe_name}/{render_type}"}
    return JSONResponse(content=response_json)

@app.get("/view/{region_name}/{render_type}")
async def view_page(region_name: str, render_type: str):
    return FileResponse("static/index.html")

@app.websocket("/ws/{region_name}/{render_type}")
async def websocket_endpoint(websocket: WebSocket, region_name: str, render_type: str):
    await websocket.accept()

    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', region_name)
    safe_type = re.sub(r'[^a-zA-Z0-9_\-]', '_', render_type)
    channel_name = f"region:{safe_name}:{safe_type}"
    latest_key = f"latest:{safe_name}:{safe_type}"

    # First send the latest state if available
    latest_data = await redis_client.get(latest_key)
    if latest_data:
        try:
            await websocket.send_text(latest_data)
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
            return

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel_name)

    # Task to listen to Redis and forward to WebSocket
    async def redis_reader():
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await websocket.send_text(message['data'])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis reader error: {e}")

    redis_task = asyncio.create_task(redis_reader())

    try:
        # Task to listen to WebSocket (to detect client disconnect)
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel_name}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        redis_task.cancel()
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
