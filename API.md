# Interface and API Documentation

This document describes the overall architecture, application interface, and API endpoints for the Second Life Media microservice.

## Architecture Overview

The application is a **Python-based FastAPI microservice** that renders real-time data visualization images using **Pillow (PIL)**. The service is designed to run in a **Kubernetes (k8s)** environment where pods are ephemeral.

To support real-time animated streaming (`multipart/x-mixed-replace`) over MJPEG across potentially multiple pod replicas without shared state, it uses **Redis Pub/Sub**.
When a `POST` request with state data is received, the app computes a series of intermediate frames to produce an animation (crossfading text, sliding rows, etc.). The application uses a global **`ProcessPoolExecutor`** (initialized via FastAPI lifespan) to parallelize CPU-bound **PIL** image generation. To avoid pickling overhead, worker processes receive raw JSON payloads and return encoded JPEG bytes directly.

Animation frames rendered in parallel are collected, sorted chronologically by frame index, and published to Redis sequentially with a **0.125s delay** to maintain a target 8fps for the MJPEG stream. Animations are configured to run for 32 frames, resulting in a total animation duration of 4 seconds.

To prevent frame interleaving during high-frequency concurrent updates, rendering endpoints use a **Redis lock** with a 5-second timeout and a unique UUID to ensure safe deletion. If the lock is unavailable, the application immediately skips the redundant rendering process rather than retrying or queuing it.

Clients (such as Second Life Moap clients) connect to the `GET /stream/{region_name}/{render_type}` endpoint, which returns a `StreamingResponse` that listens to the corresponding Redis channel and pushes frames to the client as they arrive.

## Data Structures

The primary data payloads and internal states are represented by the following classes:

### `RenderRequest` (Pydantic BaseModel)
The expected JSON payload when triggering a new render.
- `data`: Optional dict containing the current state (`users` for sim, `zones` for zone).
- `previousData`: Optional dict containing the previous state, used for calculating animations.
- `regionName`: String representing the region. Defaults to "Unknown Region".
- `type`: String, either `"sim"` or `"zone"`.
- `primsHistory`: Optional list of integers for historical prim counts.

### `RenderableUser`
Represents an individual user/agent in the "sim" rendering mode.
- Extracts details from the JSON like `uuid`, `name`, `category`, `isOOC`, `isChar`, `total` / `active` scripts, `time`, `memory`, and `complexity`.
- Tracks previous states and calculates if a value has changed to drive animations.

### `RenderableZone`
Represents a sub-region or parcel in the "zone" rendering mode.
- Extracts details from the JSON like `uuid`, `name`, `isDynamic`, `occupancy`, `rezStatus`, and `liEst`.
- Tracks previous states and calculates if a value has changed to drive animations.

## API Endpoints

### 1. Health Check
```http
GET /health
```
Returns a simple JSON status to verify the service is running. Useful for k8s liveness/readiness probes.
**Response:**
```json
{
  "status": "ok"
}
```

### 2. Render State Data
```http
POST /
POST /render
```
Accepts JSON payload conforming to the `RenderRequest` model.
This endpoint calculates animation frames based on the difference between `data` and `previousData`, renders them as JPEGs, and publishes them to the Redis Pub/Sub channel. The final frame is also cached in Redis as the latest state.

**Request Body:** `RenderRequest`

**Response:**
Returns a JSON payload with the permanent stream URL for the requested region and render type.
```json
{
  "url": "http://<host>/stream/<safe_region_name>/<render_type>"
}
```

### 3. Stream MJPEG Frames
```http
GET /stream/{region_name}/{render_type}
```
Initiates a long-lived connection that streams animated JPEG frames to the client using `multipart/x-mixed-replace`.
Upon connection, it attempts to fetch the latest cached frame for the region. Then it subscribes to the corresponding Redis channel and waits for new frames published by the `/render` endpoint.

**Path Parameters:**
- `region_name`: The name of the region (will be sanitized for safety).
- `render_type`: The type of stream, typically "sim" or "zone".

**Response:**
`StreamingResponse` with `media_type="multipart/x-mixed-replace; boundary=frame"`.

**Client-Specific Requirements:**
- **MoaP / CEF Clients (Second Life):**
  - **Multipart Boundaries:** When streaming `multipart/x-mixed-replace` MJPEG, the multipart boundary (e.g., `--frame\r\n`) must be appended at the end of each frame's payload rather than prepended. An initial boundary is sent when the stream starts. This ensures the browser engine immediately recognizes the frame as complete.
  - **Content-Length:** Each frame in the stream must include a `Content-Length` header. This ensures the viewer buffers the entire byte payload before swapping the image, preventing blank flashes.
  - **Keep-Alive Heartbeat:** To prevent MJPEG stream connections from being forcibly closed due to idle timeouts by the Kubernetes Ingress or Second Life MoaP client, the `stream_generator` implements a keep-alive heartbeat. It uses a 5-second timeout on Redis PubSub listens, yielding the latest cached frame if no new updates arrive.

### 4. Stream HEAD Request
```http
HEAD /stream/{region_name}/{render_type}
```
Provides headers for the stream endpoint without initiating the stream itself.
Used by some clients to verify content type or stream existence before connecting.

**Response:**
Returns a 200 OK with `media_type="multipart/x-mixed-replace; boundary=frame"`.
