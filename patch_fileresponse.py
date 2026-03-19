import re

with open('app.py', 'r') as f:
    content = f.read()

# Make sure FileResponse is imported
if 'FileResponse' not in content[:500]:
    content = content.replace('from fastapi.responses import JSONResponse', 'from fastapi.responses import JSONResponse, FileResponse')

with open('app.py', 'w') as f:
    f.write(content)
