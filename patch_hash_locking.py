import re

with open('app.py', 'r') as f:
    content = f.read()

# Make sure hashlib and json are imported
if 'import hashlib' not in content:
    content = content.replace('import uuid', 'import uuid\nimport hashlib\nimport json')

# We need to replace the `render` function from `safe_name = ...` to `return JSONResponse(...)`
start_idx = content.find("    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', regionName)")
end_idx = content.find("    return JSONResponse(content={\"url\": f\"{base_url}/static/{filename}\"})") + len("    return JSONResponse(content={\"url\": f\"{base_url}/static/{filename}\"})") + 1

hash_logic = """    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', regionName)

    # Generate a deterministic hash based on the payload
    payload_dict = {
        "regionName": regionName,
        "type": render_type,
        "data": data,
        "previousData": prev_data,
        "primsHistory": primsHistory
    }
    payload_str = json.dumps(payload_dict, sort_keys=True)
    payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()

    filename = f"{safe_name}_{render_type}_{payload_hash}.gif"
    filepath = os.path.join("static", filename)
    lock_filepath = os.path.join("static", f"{filename}.lock")

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    scheme = forwarded_proto if forwarded_proto else ("https" if request.url.scheme == "https" else "http")
    host = forwarded_host if forwarded_host else request.headers.get("host", "localhost:8000")
    base_url = f"{scheme}://{host}"

    response_json = {"url": f"{base_url}/static/{filename}"}

    # 1. If the fully generated GIF already exists, we are done!
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return JSONResponse(content=response_json)

    # 2. Try to acquire an exclusive file lock to generate it
    try:
        # os.O_CREAT | os.O_EXCL ensures this is an atomic operation.
        # If the file exists, it raises a FileExistsError.
        fd = os.open(lock_filepath, os.O_CREAT | os.O_EXCL | os.O_RDWR)

        try:
            # We got the lock! We are the chosen pod to render the GIF.
            if render_type == "zone":
                images = render_zone(data, prev_data, regionName, primsHistory)
            else:
                images = render_sim(data, prev_data, regionName)

            if images:
                if len(images) > 1:
                    images[0].save(filepath, save_all=True, append_images=images[1:], duration=125, loop=0)
                else:
                    images[0].save(filepath)
        finally:
            # Always close the file descriptor and remove the lock when done,
            # even if an exception occurs during rendering.
            os.close(fd)
            if os.path.exists(lock_filepath):
                os.remove(lock_filepath)

    except FileExistsError:
        # 3. Another pod/thread is already generating this exact GIF!
        # We don't need to do any work. The client will GET the file,
        # and our 30-second polling loop in the GET endpoint will handle the wait.
        pass

    return JSONResponse(content=response_json)
"""

# We also need to remove the previous `render_zone` and `render_sim` calls
# that were happening *before* the hash logic.
# Find the start of the render function
def_render_idx = content.find("async def render(request: Request, payload: RenderRequest):")
# Find the start of the `if render_type == "zone":` block that we want to remove
old_render_call_idx = content.find("    if render_type == \"zone\":", def_render_idx)

# Replace the whole chunk from old_render_call_idx to end_idx with our new hash_logic
content = content[:old_render_call_idx] + hash_logic + content[end_idx:]

with open('app.py', 'w') as f:
    f.write(content)
