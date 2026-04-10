# Interface and API Documentation

This document describes the overall architecture, application interface, and API endpoints for the Second Life Media microservice.

## Architecture Overview

The application is a **Python-based FastAPI microservice** that serves a real-time data visualization dashboard. The service is designed to run in a **Kubernetes (k8s)** environment where pods are ephemeral.

To support real-time animated streaming across potentially multiple pod replicas without shared state, it uses **Redis Pub/Sub** and **WebSockets**.
When a `POST` request with state data is received, the app saves the raw JSON to Redis and broadcasts it via a Redis Pub/Sub channel.

Clients (such as Second Life Moap clients via CEF browsers) connect to the `GET /view/{region_name}/{render_type}` endpoint, which serves a static HTML/CSS/JS web application. The frontend JavaScript establishes a WebSocket connection to `WS /ws/{region_name}/{render_type}`. The server immediately pushes the latest cached JSON state, then listens to the Redis channel and pushes subsequent updates to the browser. The browser handles layout, DOM diffing, and CSS animations entirely on the client side.

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
Accepts JSON payload. Extracts the current `data` and drops `previousData` (as client-side JS is stateful and handles its own diffing). Serializes the payload and pushes it to the Redis channel `region:{safe_name}:{render_type}` and caches it under `latest:{safe_name}:{render_type}`.

**Request Body Example:**
```json
{
    "data": {"users": [...]},
    "regionName": "My Region",
    "type": "sim"
}
```

**Response:**
Returns a JSON payload with the permanent view URL for the requested region and render type. This triggers a redirect in the client wrapper to load the web page.
```json
{
  "url": "https://<host>/view/<safe_region_name>/<render_type>"
}
```

### 3. View Dashboard (HTML)
```http
GET /view/{region_name}/{render_type}
```
Serves the `index.html` static file. The JS bundled with it reads the URL path to determine what state to connect to and render.

### 4. WebSocket Data Stream
```http
WS /ws/{region_name}/{render_type}
```
Initiates a WebSocket connection for the frontend browser.
Upon connection, the server immediately sends the latest cached JSON string from Redis so the frontend populates instantly.
The server then subscribes to the Redis Pub/Sub channel and pushes any new JSON payloads received from the `/render` POST endpoint directly to the browser.

**Client-Side Behavior:**
- The JavaScript client maintains the current state in memory.
- When a new WebSocket message arrives, it diffs the JSON against its local state.
- It dynamically updates the DOM and applies CSS animations (e.g., `transform: translateY` for sliding rows, CSS `animation` keyframes for color flashes on updated values) to create a smooth, cyberpunk-themed visualization.
