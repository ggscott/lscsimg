import re

with open('app.py', 'r') as f:
    content = f.read()

# Make sure base64 and JSONResponse are imported
if 'import base64' not in content:
    content = content.replace('import io\n', 'import io\nimport base64\n')

if 'from fastapi.responses import JSONResponse' not in content:
    content = content.replace('from fastapi.responses import Response', 'from fastapi.responses import Response, JSONResponse')
else:
    # Just remove Response if we are importing JSONResponse already
    pass

# We need to replace the end of the `render` function.
start_idx = content.find("    img_io = io.BytesIO()")
end_idx = content.find("if __name__ == \"__main__\":")

base64_logic = """    img_io = io.BytesIO()
    if len(images) > 1:
        images[0].save(img_io, format='GIF', save_all=True, append_images=images[1:], duration=125, loop=0)
    else:
        images[0].save(img_io, format='GIF')

    img_data = img_io.getvalue()
    base64_encoded = base64.b64encode(img_data).decode('utf-8')
    data_uri = f"data:image/gif;base64,{base64_encoded}"

    return JSONResponse(content={"url": data_uri})

"""

content = content[:start_idx] + base64_logic + content[end_idx:]

with open('app.py', 'w') as f:
    f.write(content)
