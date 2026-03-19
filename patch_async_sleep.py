import re

with open('app.py', 'r') as f:
    content = f.read()

# Replace time.sleep with asyncio.sleep
if 'import asyncio' not in content:
    content = content.replace('import time\n', 'import time\nimport asyncio\n')

content = content.replace('time.sleep(1.0)', 'await asyncio.sleep(1.0)')

with open('app.py', 'w') as f:
    f.write(content)
