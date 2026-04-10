import re

with open("app.py", "r") as f:
    content = f.read()

# We need to replace the entire try...finally block in websocket_endpoint
pattern = r"    pubsub = redis_client\.pubsub\(\)\n    await pubsub\.subscribe\(channel_name\)\n\n    try:\n        while True:.*?await pubsub\.close\(\)"

replacement = """    pubsub = redis_client.pubsub()
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
        await pubsub.close()"""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("app.py", "w") as f:
    f.write(new_content)
