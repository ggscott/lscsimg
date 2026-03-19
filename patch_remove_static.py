with open('app.py', 'r') as f:
    content = f.read()

content = content.replace('app.mount("/static", StaticFiles(directory="static"), name="static")', '# Removed static mount')
content = content.replace('os.makedirs("static", exist_ok=True)', '# Removed static directory creation')
content = content.replace('from fastapi.staticfiles import StaticFiles', '# from fastapi.staticfiles import StaticFiles')

with open('app.py', 'w') as f:
    f.write(content)
