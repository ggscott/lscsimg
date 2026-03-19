import re

with open('app.py', 'r') as f:
    content = f.read()

# Add io import
if 'import io' not in content:
    content = content.replace('import os', 'import os\nimport io\nfrom fastapi.responses import Response')

# Update the render function response
# Find the end of render_zone call
start_idx = content.find("if render_type == \"zone\":")
end_idx = content.find("forwarded_proto = request.headers.get(\"x-forwarded-proto\")", start_idx)

# Replace the saving logic with streaming logic
streaming_logic = """    if render_type == "zone":
        images = render_zone(data, prev_data, regionName, primsHistory)
    else:
        images = render_sim(data, prev_data, regionName)

    if not images:
        return JSONResponse(status_code=500, content={"detail": "Failed to generate image."})

    img_io = io.BytesIO()
    if len(images) > 1:
        images[0].save(img_io, format='GIF', save_all=True, append_images=images[1:], duration=125, loop=0)
    else:
        images[0].save(img_io, format='GIF')

    img_io.seek(0)

"""

content = content[:start_idx] + streaming_logic + "    return Response(content=img_io.getvalue(), media_type=\"image/gif\")\n\n" + content[content.find("if __name__ == \"__main__\":"):]

with open('app.py', 'w') as f:
    f.write(content)
