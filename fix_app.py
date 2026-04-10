with open("app.py", "r") as f:
    content = f.read()

content = content.replace(
    "                await websocket.send_text(message['data'])",
    """                await websocket.send_text(message['data'])

            # Non-blocking receive to check if client disconnected
            try:
                # If receive gets a message, we do nothing with it.
                # If it raises WebSocketDisconnect, the except block below catches it.
                # Use a small timeout or no-wait if possible, but asyncio.wait_for is standard
                await asyncio.wait_for(websocket.receive(), timeout=0.01)
            except asyncio.TimeoutError:
                pass"""
)

with open("app.py", "w") as f:
    f.write(content)
