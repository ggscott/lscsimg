import re

with open('app.py', 'r') as f:
    content = f.read()

# Add missing imports for the custom endpoint and sleeping
if 'import time' not in content:
    content = content.replace('import os\n', 'import os\nimport time\n')

if 'from fastapi.responses import FileResponse' not in content:
    content = content.replace('from fastapi.responses import Response, JSONResponse', 'from fastapi.responses import Response, JSONResponse, FileResponse')

if 'from fastapi import FastAPI, Request, HTTPException' not in content:
    content = content.replace('from fastapi import FastAPI, Request\n', 'from fastapi import FastAPI, Request, HTTPException\n')

# Re-add static directory creation
if '# Removed static directory creation' in content:
    content = content.replace('# Removed static directory creation', 'os.makedirs("static", exist_ok=True)')

# Find the end of the `render` function (before the main block)
start_idx = content.find("    img_io = io.BytesIO()")
end_idx = content.find("if __name__ == \"__main__\":")

file_write_logic = """    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', regionName)
    unique_id = uuid.uuid4().hex
    filename = f"{safe_name}_{render_type}_{unique_id}.gif"
    filepath = os.path.join("static", filename)

    if len(images) > 1:
        images[0].save(filepath, save_all=True, append_images=images[1:], duration=125, loop=0)
    else:
        images[0].save(filepath)

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    scheme = forwarded_proto if forwarded_proto else ("https" if request.url.scheme == "https" else "http")
    host = forwarded_host if forwarded_host else request.headers.get("host", "localhost:8000")
    base_url = f"{scheme}://{host}"

    return JSONResponse(content={"url": f"{base_url}/static/{filename}"})

@app.get("/static/{filename}")
async def get_static_file(filename: str):
    filepath = os.path.join("static", filename)

    # Prevent directory traversal
    if not os.path.abspath(filepath).startswith(os.path.abspath("static")):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Poll up to 15 times, waiting 1 second between checks
    for _ in range(15):
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return FileResponse(filepath, media_type="image/gif")
        time.sleep(1.0)

    raise HTTPException(status_code=404, detail="File not found")

"""

content = content[:start_idx] + file_write_logic + content[end_idx:]

with open('app.py', 'w') as f:
    f.write(content)
