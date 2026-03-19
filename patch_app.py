import re

with open('app.py', 'r') as f:
    content = f.read()

# Add uuid import if not present
if 'import uuid' not in content:
    content = content.replace('import os', 'import os\nimport uuid')

# Update filename generation in render function
pattern = r'filename = f"\{safe_name\}_\{render_type\}\.gif"'
replacement = r'unique_id = uuid.uuid4().hex\n    filename = f"{safe_name}_{render_type}_{unique_id}.gif"'

content = re.sub(pattern, replacement, content)

with open('app.py', 'w') as f:
    f.write(content)
